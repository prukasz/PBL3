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
        self.latest_beacons = []
        self.scan_lock = asyncio.Lock()

    def _motion_callback_bridge(self):
        if self.main_loop and not self.main_loop.is_closed():
            print("[TAG] Motion Detected")
            self.main_loop.call_soon_threadsafe(self.motion_event.set)

    async def run_event_loop(self):
        self.main_loop = asyncio.get_running_loop()
        self.mpu.register_callback(self._motion_callback_bridge)
        
        print("[TAG] Entering Logic Loop")
        
        scan_task = asyncio.create_task(self.continuous_scan_loop())
    
        try:
            while True:
                self.mpu.start_detection()
                print("[TAG] Waiting for movement")
                
                await self.motion_event.wait()
                self.motion_event.clear()
                
                # Run the cycle
                await self.advertise_latest_beacons()

                print("[TAG] Advertise cycle complete")
        finally:
            scan_task.cancel()

    # Stara funckja nie używana nie uwgzlędnia skanowania ciągłego alarmu
    # async def run_cycle(self):
    #     print(f"[TAG] Cycle Started. Scanning for {self.scan_time}s")
    #     try:
    #         raw_beacons = await self.ble.scan(duration=self.scan_time)
            
    #         selected_beacons = self.processor.get_specific_beacons(raw_beacons)
    #         sorted_beacons = self.processor.sort_by_rssi(selected_beacons)
            
    #         if sorted_beacons:
    #             print(f"[TAG] Found {len(sorted_beacons)} compliant beacons")
    #             print(f"[TAG] Advertising for {self.adv_time}s")
                
    #             await self.ble.advertise(
    #                 time=self.adv_time, 
    #                 period=self.adv_period, 
    #                 payload=self.processor.get_payload(sorted_beacons)
    #             )
    #             print("[TAG] Advertising Finished")
    #         else:
    #             print("[TAG] No beacons found")
                
    #     except Exception as e:
    #         print(f"[TAG] Cycle Error: {e}")

    async def continuous_scan_loop(self):
        while True:
            async with self.scan_lock:
                print(f"[SCAN] Scanning for {self.scan_time}s")
                try:
                    raw_beacons = await self.ble.scan(duration=self.scan_time)
                    self.latest_beacons = self.processor.get_specific_beacons(raw_beacons)
                    self.latest_beacons = self.processor.sort_by_rssi(self.latest_beacons)
                    print(f"[SCAN] Found {len(self.latest_beacons)} beacons")
                except Exception as e:
                    print(f"[SCAN] Error: {e}")
            
            await asyncio.sleep(0.1)


    async def advertise_latest_beacons(self):
        async with self.scan_lock:
            if self.latest_beacons:
                print(f"[TAG] Advertising {len(self.latest_beacons)} beacons for {self.adv_time}s")
                try:
                    await self.ble.advertise(
                        time=self.adv_time, 
                        period=self.adv_period, 
                        payload=self.processor.get_payload(self.latest_beacons)
                    )
                    print("[TAG] Advertising Finished")
                except Exception as e:
                    print(f"[TAG] Advertise Error: {e}")
            else:
                print("[TAG] No beacons to advertise")