from Ble_conn import BLEInterface
from Data_processing import DataProcessor
from pprint import pprint
from typing import List, Dict

class Tag:
    def __init__(self, ble_adapter: BLEInterface, data_processor: DataProcessor, adv_time: int, adv_period: int, scan_time: int):
        self.ble = ble_adapter #DI
        self.processor = data_processor #DI
        self.scan_time = scan_time
        self.adv_time = adv_time
        self.adv_period = adv_period

    async def run_cycle(self):
        print(f"[TAG] Scanning for {self.scan_time} seconds")
        raw_beacons = await self.ble.scan(duration=self.scan_time)
        
        #pprint(raw_beacons)

        selected_beacons = self.processor.get_specific_beacons(raw_beacons)
        sorted_beacons = self.processor.sort_by_rssi(selected_beacons)
        
        if sorted_beacons:
            print(f"[TAG] Found {len(sorted_beacons)} compliant beacons:")
            for dev in sorted_beacons:
                print(f"\"{dev['mac']}\":{dev['rssi']}")
        else:
            print("No compliant beacons found")

        print(f"[TAG] Advertising for {self.adv_time}s...")
        success = await self.ble.advertise(time=self.adv_time, period=self.adv_period, payload=self.processor.get_payload(sorted_beacons))
            
        if success:
            print("[TAG] Advertising finished successfully")
        else:
            print("[TAG] Advertising failed")

    async def scan_only(self)->List[Dict]: 
        print(f"[TAG] Scanning for {self.scan_time} seconds")
        raw_beacons = await self.ble.scan(duration=self.scan_time)
        selected_beacons = self.processor.get_specific_beacons(raw_beacons)
        sorted_beacons = self.processor.sort_by_rssi(selected_beacons)
        pprint(sorted_beacons)
        return sorted_beacons
