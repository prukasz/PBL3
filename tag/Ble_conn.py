from abc import ABC, abstractmethod
from bleak import BleakScanner, BLEDevice, AdvertisementData
import asyncio
import subprocess
import struct

class BLEInterface(ABC):
    def __init__(self):
        self.adapter = "hci0"                   
    @abstractmethod
    async def scan(self, duration: int) -> list:
        pass
    @abstractmethod
    async def advertise(self, time: int, period: int, payload: str) -> bool:
        pass

class BleakBLEInterface(BLEInterface):
    _is_scanning = False
    _is_advertising = False

    def __init__(self):
        super().__init__()
        self.__found_devices = {}
        self.mac = None  

    async def initialize(self):
        await self.get_own_mac()
        await self.__run_hci_command(["sudo", "hciconfig", self.adapter, "up"])

    async def get_own_mac(self):
        try:
            result = await asyncio.to_thread(subprocess.run, ["hcitool", "dev"], capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout
                for line in output.split('\n'):
                    if self.adapter in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            self.mac = parts[1].upper().replace(':', '')
                            print(f"[Bleak interface] MAC found: {self.mac}")
                            return 
            self.mac = "000000000000"
            print("[Bleak interface] MAC not found, using default.")
        except Exception as e:
            print(f"[Bleak interface] Error getting MAC: {e}")
            self.mac = "000000000000"

    @staticmethod
    async def __run_hci_command(args: list) -> bool:
        try:
            result = await asyncio.to_thread(subprocess.run, args, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[Bleak interface] Command failed: {result.stderr.strip()}")
                return False
            return True
        except Exception as e:
            print(f"[Bleak interface] Subprocess error: {e}")
            return False
    
    async def scan(self, duration: int) -> list:
        if BleakBLEInterface._is_scanning or BleakBLEInterface._is_advertising:
            print(f"[BLE] SKIPPING SCAN: Busy")
            return []
        
        BleakBLEInterface._is_scanning = True
        
        await self.__run_hci_command(["sudo", "hciconfig", self.adapter, "up"])
        await asyncio.sleep(1)

        try:
            self.__found_devices = {} 
            scanner = BleakScanner(detection_callback=self.__scan_callback)
            
            await scanner.start() 
            await asyncio.sleep(duration)
            await scanner.stop()  
            
            #Avreaging
            results = []
            for device_data in self.__found_devices.values():
                # Extract history and calculate average
                history = device_data.pop('rssi_history', [])
                if history:
                    avg_rssi = sum(history) / len(history)
                    device_data['rssi'] = round(avg_rssi, 2)
                else:
                    device_data['rssi'] = -100

                results.append(device_data)
            
            return results
            
        except Exception as e:
            print(f"[BLE] SCAN CRASHED: {e}")
            return []
        finally:
            BleakBLEInterface._is_scanning = False

    def __scan_callback(self, device: BLEDevice, adv_data: AdvertisementData):
        if device.address not in self.__found_devices:
            # First time seeing this device: initialize list
            self.__found_devices[device.address] = {
                'mac': device.address,
                'rssi_history': [adv_data.rssi], # Start history list
                'name': device.name or "N/A",
                'uuid': adv_data.service_uuids,
                'txpow': adv_data.tx_power,
                'mdata': adv_data.manufacturer_data
            }
        else:
            self.__found_devices[device.address]['rssi_history'].append(adv_data.rssi)
            #Update name if it appears later
            if self.__found_devices[device.address]['name'] == "N/A" and device.name:
                self.__found_devices[device.address]['name'] = device.name
    
    async def advertise(self, time: int, period: int, payload: str) -> bool:
        if BleakBLEInterface._is_advertising or BleakBLEInterface._is_scanning:
            print("[BLE] cannot advertise (busy)")
            return False
            
        print("[Bleak interface] Starting advertising...")
        BleakBLEInterface._is_advertising = True
        
        cmd_prefix = ["sudo", "hcitool", "-i", self.adapter, "cmd"]
        cmd_scan_disable = cmd_prefix + ["0x08", "0x000C", "00", "00"]
        cmd_adv_disable = cmd_prefix + ["0x08", "0x000A", "00"]

        try:        
            await self.__run_hci_command(cmd_scan_disable)
            await self.__run_hci_command(cmd_adv_disable)

            min_time = int(period / 0.625)
            min_time = max(32, min(min_time, 16384))
            max_time = min_time + 32 
            packed_time = struct.pack('<HH', min_time, max_time) 
            time_args = [f"{b:02X}" for b in packed_time]

            cmd_adv_params = cmd_prefix + ["0x08", "0x0006"] + time_args + ["03", "00", "00", "00", "00", "00", "00", "00", "00", "07", "00"]
            cmd_adv_data = cmd_prefix + ["0x08", "0x0008"] + payload.split()  
            cmd_enable = cmd_prefix + ["0x08", "0x000A", "01"]

            if not await self.__run_hci_command(cmd_adv_data): return False
            if not await self.__run_hci_command(cmd_adv_params): return False
            if not await self.__run_hci_command(cmd_enable): return False
            
            await asyncio.sleep(time)
            return True
            
        except Exception as e:
            print(f"[Bleak interface] Advertising error: {e}")
            return False

        finally:
            # Cleanup
            await self.__run_hci_command(cmd_adv_disable)
            BleakBLEInterface._is_advertising = False
            await asyncio.sleep(2)