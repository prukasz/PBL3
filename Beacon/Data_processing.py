from abc import ABC, abstractmethod
from typing import List, Dict
import struct

class BeaconDataProcessor(ABC):

    @abstractmethod
    def get_tags(self, devices: List[Dict]) -> List[Dict]:
        pass
    @abstractmethod
    def get_alarm_payload(self, payload: str) -> str:
        pass

class BeaconDataFilter(BeaconDataProcessor):
    def __init__(self):
        super().__init__()

    def get_tags(self, devices: List[Dict]) -> List[Dict]:
        tags = []
        target_manufacturer_id = 0xFFFF  # Manufacturer ID for tags

        for device in devices:
            mdata = device.get('mdata', {})
            if target_manufacturer_id in mdata:
                tags.append(device)

        return tags

    def get_alarm_payload(self, payload: str) -> str:

        data = list(bytes.fromhex(payload))
        
        company_id = [0xFF, 0xFE]    #company id
        flags = [0x02, 0x01, 0x06]   #flags field
        
        data_len = 3 + len(data)     #length of data field + company id + length of custom payload
        payload_bytes = flags + [data_len, 0xFF] + company_id + data   #total created payload
        total_data_len = len(payload_bytes)
        padding_needed = 31 - total_data_len
        padding = [0x00] * padding_needed      #padding to 31
        final_packet = [total_data_len] + payload_bytes + padding
        return " ".join(f"{b:02X}" for b in final_packet)  #join add prefix and return 
