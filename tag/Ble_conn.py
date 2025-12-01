from abc import ABC, abstractmethod
from bleak import BleakScanner, BLEDevice, AdvertisementData
import asyncio
import subprocess
import struct

#contract
class BLEInterface(ABC):
    def __init__(self):
        self.adapter = "hci0" 
                          
    @abstractmethod
    async def scan(self, duration: int) -> list:
        pass
    
    @abstractmethod
    async def advertise(self, time: int, period: int, payload: str) -> bool:
        pass

#bleak class
class BleakBLEInterface(BLEInterface):
    _is_scanning = False
    _is_advertising = False

    def __init__(self):
        super().__init__()
        self.__found_devices = {}

    #common
    @staticmethod
    async def __run_hci_command(args: list) -> bool:
        try:
            result = await asyncio.to_thread(
                subprocess.run, 
                args, 
                capture_output=True, 
                text=True          
            )

            if result.returncode != 0:
                #cmd errors
                print(f"[Bleak interface]Command failed: {result.stderr.strip()}")
                return False
            return True
        
        except Exception as e:
            print(f"[Bleak interface]Subprocess error: {e}")
            return False
    
    #ble scanning (returns all unique devices found)
    async def scan(self, duration: int) -> list:
        if BleakBLEInterface._is_scanning or BleakBLEInterface._is_advertising:
            return []
        
        BleakBLEInterface._is_scanning = True
        try:
            self.__found_devices = {} #clean list 
            scanner = BleakScanner(detection_callback=self.__scan_callback)
            await scanner.start() #run bleak method
            await asyncio.sleep(duration) #wait for scan to end
            await scanner.stop()  #run bleak method
            return list(self.__found_devices.values()) #return list of all devices (list of dict)
        except Exception:
            return []
        finally:
            BleakBLEInterface._is_scanning = False

    #callback used by bleak scanner 
    def __scan_callback(self, device: BLEDevice, adv_data: AdvertisementData):
        #check if device already in list 
        if device.address not in self.__found_devices:
            #if not add it 
            self.__found_devices[device.address] = {
                'mac': device.address,
                'rssi': adv_data.rssi,
                'name': device.name or "N/A",
                'uuid': adv_data.service_uuids,
                'txpow': adv_data.tx_power,
                'mdata': adv_data.manufacturer_data
            }
    
    async def advertise(self, time: int, period: int, payload: str) -> bool:
        if BleakBLEInterface._is_advertising or BleakBLEInterface._is_scanning:
            return False
        print("[Bleak interface] starting advetising")
        BleakBLEInterface._is_advertising = True
        
        cmd_prefix = ["sudo", "hcitool", "-i", self.adapter, "cmd"]
        
        cmd_scan_disable = cmd_prefix + ["0x08", "0x000C", "00", "00"]
        cmd_adv_disable = cmd_prefix + ["0x08", "0x000A", "00"]

        try:
            await self.__run_hci_command(["sudo", "hciconfig", self.adapter, "down"])
            await self.__run_hci_command(["sudo", "hciconfig", self.adapter, "up"])
            await asyncio.sleep(0.5) #wait after reset

            await self.__run_hci_command(cmd_scan_disable)
            await self.__run_hci_command(cmd_adv_disable)
            #convert provided adv period into cmd values
            min_time = int(period / 0.625)
            min_time = max(32, min(min_time, 16384))
            max_time = min_time + 32 
            
            packed_time = struct.pack('<HH', min_time, max_time) 
            time_args = [f"{b:02X}" for b in packed_time]  #convert to paste ready 

            cmd_adv_params = cmd_prefix + ["0x08", "0x0006"] + time_args + [ # merge with time
                "03", "00", "00", "00", "00", "00", "00", "00", "00", "07", "00"
            ]
            
            cmd_adv_data = cmd_prefix + ["0x08", "0x0008"] + payload.split()  
            cmd_enable = cmd_prefix + ["0x08", "0x000A", "01"]

            if not await self.__run_hci_command(cmd_adv_data): return False
            if not await self.__run_hci_command(cmd_adv_params): return False
            if not await self.__run_hci_command(cmd_enable): return False
            #wait for set duration
            await asyncio.sleep(time)
            return True
            
        except Exception as e:
            print(f"[Bleak interface] Advertising error: {e}")
            return False

        finally:
            await self.__run_hci_command(cmd_adv_disable)
            BleakBLEInterface._is_advertising = False