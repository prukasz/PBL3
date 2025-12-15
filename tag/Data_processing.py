from abc import ABC, abstractmethod
from typing import List, Dict
import struct

class DataProcessor(ABC):
    @abstractmethod
    def sort_by_rssi(self, devices: List[Dict]) -> List[Dict]: pass
    @abstractmethod
    def get_specific_beacons(self, devices: List[Dict]) -> List[Dict]: pass
    @abstractmethod
    def get_payload(self,  devices: List[Dict]) -> str: pass

class DataFilter(DataProcessor):
    def __init__(self,  target_macs: List[str], my_mac):
        super().__init__()
        self.target_macs = target_macs
        self.my_mac = my_mac
    
    def sort_by_rssi(self, devices: List[Dict]) -> List[Dict]:
        valid_beacons = [d for d in devices if d.get('rssi') is not None]
        return sorted(valid_beacons, key=lambda x: x['rssi'], reverse=True)

    def get_specific_beacons(self, devices: List[Dict]) -> List[Dict]:
        specific_beacons = []
        eddystone_uuid_part = "feaa"
        CONST_MANUFACTURER_ID = 65279 # 0xFF00

        for device in devices:
            is_match = False
            
            # 1. Whitelist Check
            if self.target_macs and device['mac'] in self.target_macs:
                mdata = device.get('mdata', {})
                # FIX: Check if key exists before accessing
                manufacturer_bytes = mdata.get(CONST_MANUFACTURER_ID)
                
                if manufacturer_bytes:
                    str_hex = (''.join(f'{b:02X}' for b in manufacturer_bytes)).replace(' ', '')
                    if str_hex.startswith(self.my_mac):
                        print(f'alarm: {str_hex.strip(self.my_mac)}')
                    is_match = True
            
            # 2. Eddystone Check
            elif device.get('uuid'):
                for uuid in device['uuid']:
                    if eddystone_uuid_part in uuid.lower():
                        is_match = True
                        break
    
            if is_match:
                specific_beacons.append(device)
                
        return specific_beacons

    def get_payload(self, devices: List[Dict]) -> str:
        top_3 = devices[:3]
        data = []
        for dev in top_3:
            clean_mac = dev['mac'].replace(":", "")
            try:
                data.extend(bytes.fromhex(clean_mac))
                rssi_packed = struct.pack('b', int(dev['rssi']))
                data.append(rssi_packed[0])
            except ValueError:
                continue

        company_id = [0xFF, 0xFF]
        flags = [0x02, 0x01, 0x06]
        data_len = 3 + len(data)
        payload_bytes = flags + [data_len, 0xFF] + company_id + data
        
        padding = [0x00] * max(0, 31 - len(payload_bytes))
        final_packet = [len(payload_bytes)] + payload_bytes + padding

        return " ".join(f"{b:02X}" for b in final_packet)