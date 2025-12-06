from Ble_conn import BLEInterface
from Wifi_conn import WifiInterface
from Data_processing import DataProcessor
from pprint import pprint


class Beacon:
    def __init__(self, wifi_adapter: WifiInterface,ble_adapter: BLEInterface, data_processor: DataProcessor, adv_time: int, adv_period: int, scan_time: int):
        self.ble = ble_adapter  # Dependency Injection
        self.processor = data_processor  # Dependency Injection
        self.scan_time = scan_time
        self.adv_time = adv_time
        self.adv_period = adv_period
        self.wifi = wifi_adapter  # Dependency Injection

    async def run_cycle(self):
        print(f"[Beacon] Scanning for {self.scan_time} seconds")
        raw_devices = await self.ble.scan(duration=self.scan_time)

        pprint(raw_devices)

        selected_tags = self.processor.get_tags(raw_devices)

        if selected_tags:
            print(f"[Beacon] Found {len(selected_tags)} compliant tags:")
            for dev in selected_tags:
                print(f"Filtered: {dev['mac']} ({dev['name']}) | Data: {''.join(['0x' + data.hex() for data in dev['mdata'].values()])}")
        else:
            print("[Beacon] No compliant tags found.")
    
        print(f"[Beacon] Advertising for {self.adv_time}s...")
        success = await self.ble.advertise(time=self.adv_time, period=self.adv_period, payload=self.processor.get_payload(selected_tags))

        if success:
            print("[Beacon] Advertising finished successfully")
        else:
            print("[Beacon] Advertising failed")

    