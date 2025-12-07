import asyncio
from Ble_conn import BleakBLEInterface
from Tag import Tag
from Data_processing import DataFilter
from FileHandler import FileHandler

SCAN_DURATION = 5    
ADV_DURATION = 1     
ADV_PERIOD_MS = 200
POINT_SCAN_CNT = 5

async def main():
    
    file_manager = FileHandler(whitelist_file="whitelist.txt", output_file="scan_results.txt")
    
    target_macs = file_manager.load_whitelist()
    if not target_macs:
        print(target_macs)

    try:
        ble_interface = BleakBLEInterface()
        data_filter = DataFilter(target_macs=target_macs)

        tag = Tag(
            ble_adapter=ble_interface,
            data_processor=data_filter,
            scan_time=SCAN_DURATION,
            adv_time=ADV_DURATION,
            adv_period=ADV_PERIOD_MS
        )

        print("Type 'S' to scan point, 'Q' to quit.")
        
        point_counter = 1

        while True:
            cmd = input(f"\n[Point {point_counter}] Ready? (S/Q): ").strip().upper()

            if cmd == 'Q':
                break
            
            elif cmd == 'S':
                print(f"Measuring Point {point_counter}")
                
                file_manager.save_point_header(point_counter)

                for i in range(1, POINT_SCAN_CNT+1):
                    print(f"Scan {i}/{POINT_SCAN_CNT}")
                    beacons = await tag.scan_only()
                    file_manager.save_scan_data(beacons)
                
                print(f"Point {point_counter} Saved")
                point_counter += 1
            
            else:
                print("Invalid command.")

    except Exception as e:
        print(f"[Main Error]: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped")