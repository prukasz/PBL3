from abc import ABC, abstractmethod
from typing import List, Dict
import struct

class DataProcessor(ABC):

    @abstractmethod
    def filter_by_rssi(self, devices: List[Dict]) -> List[Dict]:
        pass

    @abstractmethod
    def get_specific_beacons(self, devices: List[Dict]) -> List[Dict]:
        pass

    @abstractmethod
    def get_payload(self,  devices: List[Dict]) -> str:
        pass

class DataFilter(DataProcessor):
    def __init__(self,  target_macs: List[str]):
        super().__init__()
        self.target_macs = target_macs
    
    def filter_by_rssi(self, devices: List[Dict]) -> List[Dict]:

        valid_beacons = [d for d in devices if d.get('rssi') is not None]
        return sorted(valid_beacons, key=lambda x: x['rssi'], reverse=True)

    def get_specific_beacons(self, devices: List[Dict]) -> List[Dict]:
        
        specific_beacons = []
        eddystone_uuid_part = "feaa"  #Eddystone UUID first part

        for device in devices:
            is_match = False
            
            if self.target_macs and device['mac'] in self.target_macs:   #check not Eddystone whitelist
                is_match = True
            
            elif device.get('uuid'):                                     #check for Eddystone UUID
                for uuid in device['uuid']:
                    if eddystone_uuid_part in uuid.lower():
                        is_match = True
                        break
    
            if is_match:
                specific_beacons.append(device)                         #if any occur add to list
                
        return specific_beacons     #return filtered list

    #Returns ready to send payload with 3 rssi filtered devices
    def get_payload(self, devices: List[Dict]) -> str:
        top_3 = devices[:3]
        data = []
        
        for dev in top_3:
            clean_mac = dev['mac'].replace(":", "")
            data.extend(bytes.fromhex(clean_mac))
            rssi_packed = struct.pack('b', int(dev['rssi']))
            data.append(rssi_packed[0])

        company_id = [0xFF, 0xFF]    #company id 
        flags = [0x02, 0x01, 0x06]   #flags field
        
        data_len = 3 + len(data)     #length of data field + company id + length of custom payload

        payload_bytes = flags + [data_len, 0xFF] + company_id + data   #total crated payload
        
        total_data_len = len(payload_bytes)
        padding_needed = 31 - total_data_len
        padding = [0x00] * padding_needed      #paddint to 31 bytes
        
        final_packet = [total_data_len] + payload_bytes + padding

        return " ".join(f"{b:02X}" for b in final_packet)  #join add prefix and return


class DataFilterBeacon(DataFilter):
    def get_tags(self, devices: List[Dict]) -> List[Dict]:
        tags = []
        target_manufacturer_id = 0xFFFF  # Manufacturer ID for tags

        for device in devices:
            mdata = device.get('mdata', {})
            if target_manufacturer_id in mdata:
                tags.append(device)

        return tags
    
    def get_payload(self, devices: List[Dict]) -> str:
        data = []

        for dev in devices:
            clean_mac = dev['mac'].replace(":", "")
            data.extend(bytes.fromhex(clean_mac))
        
        company_id = [0xFF, 0xFE]    #company id
        flags = [0x02, 0x01, 0x06]   #flags field

        data_len = 3 + len(data)     #length of data field + company id + length of custom payload
        payload_bytes = flags + [data_len, 0xFF] + company_id + data   #total crated payload
        total_data_len = len(payload_bytes)
        padding_needed = 31 - total_data_len
        padding = [0x00] * padding_needed      #paddint to 31
        final_packet = [total_data_len] + payload_bytes + padding
        return " ".join(f"{b:02X}" for b in final_packet)  #join add prefix and return