from Ble_conn import BLEInterface
from Data_processing import DataProcessor
from Mpu6050Handler import MpuHandler
import asyncio
from typing import List, Dict

class Tag:
    def __init__(self, ble_adapter: BLEInterface, data_processor: DataProcessor, mpu_handler: MpuHandler, adv_time: int, adv_period: int, scan_time: int):
        self.ble = ble_adapter
        self.processor = data_processor
        self.mpu = mpu_handler 
        
        self.scan_time = scan_time
        self.adv_time = adv_time
        self.adv_period = adv_period
        
        self.motion_event = asyncio.Event()
        self.main_loop = None 

    def _motion_callback_bridge(self):
        if self.main_loop and not self.main_loop.is_closed():
            print("[TAG] Motion Detected")
            self.main_loop.call_soon_threadsafe(self.motion_event.set)

    async def run_event_loop(self):
        self.main_loop = asyncio.get_running_loop()
        self.mpu.register_callback(self._motion_callback_bridge)
        
        print("[TAG] Entering Logic Loop")
        
        while True:
            self.mpu.start_detection()
            print("[TAG] Waiting for movement")
            
            await self.motion_event.wait()
            self.motion_event.clear()
            
            # Run the cycle
            await self.run_cycle()

            print("[TAG] Cycle complete")

    async def run_cycle(self):
        print(f"[TAG] Cycle Started. Scanning for {self.scan_time}s")
        try:
            raw_beacons = await self.ble.scan(duration=self.scan_time)
            
            selected_beacons = self.processor.get_specific_beacons(raw_beacons)
            sorted_beacons = self.processor.sort_by_rssi(selected_beacons)
            
            if sorted_beacons:
                print(f"[TAG] Found {len(sorted_beacons)} compliant beacons")
                print(f"[TAG] Advertising for {self.adv_time}s")
                
                await self.ble.advertise(
                    time=self.adv_time, 
                    period=self.adv_period, 
                    payload=self.processor.get_payload(sorted_beacons)
                )
                print("[TAG] Advertising Finished")
            else:
                print("[TAG] No beacons found")
                
        except Exception as e:
            print(f"[TAG] Cycle Error: {e}")