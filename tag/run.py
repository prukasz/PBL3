import asyncio
from Ble_conn import BleakBLEInterface
from Data_processing import DataFilter
from FileHandler import FileHandler
from Tag import Tag


async def main():

    file_manager = FileHandler(whitelist_file="whitelist.txt", output_file="")
    target_macs = file_manager.load_whitelist()
    
    SCAN_DURATION = 10
    ADV_DURATION = 10
    ADV_PERIOD_MS = 200

    try:
        ble_interface = BleakBLEInterface()
        data_filter = DataFilter(target_macs=target_macs)

        tag = Tag(
            ble_adapter=ble_interface, #DI
            data_processor=data_filter, #DI
            scan_time=SCAN_DURATION,
            adv_time=ADV_DURATION,
            adv_period=ADV_PERIOD_MS
        )
        while True:        #run in loop
            await tag.run_cycle()

    except Exception as e:
        print(f"[main], error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")