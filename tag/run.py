import asyncio
from Ble_conn import BleakBLEInterface
from Data_processing import DataFilter
from FileHandler import FileHandler
from Mpu6050Handler import MpuHandler
from Tag import Tag

async def main():

    file_manager = FileHandler(whitelist_file="whitelist.txt", output_file="")
    target_macs = file_manager.load_whitelist()
    
    SCAN_DURATION = 10
    ADV_DURATION = 10
    ADV_PERIOD_MS = 200
    INTERRUPT_PIN = 17

    try:
        # Initialize BLE
        ble_interface = BleakBLEInterface()
        await ble_interface.initialize()
        
        # Initialize Data Filter
        data_filter = DataFilter(target_macs=target_macs, my_mac=ble_interface.mac)

        # Initialize MPU 
        mpu = MpuHandler(pin=INTERRUPT_PIN)
        mpu.initialize()

        tag = Tag(
            ble_adapter=ble_interface,
            data_processor=data_filter,
            mpu_handler=mpu, 
            scan_time=SCAN_DURATION,
            adv_time=ADV_DURATION,
            adv_period=ADV_PERIOD_MS
        )
        await tag.run_event_loop()

    except Exception as e:
        print(f"[run] error: {e}")
    finally:
        try:
            mpu.cleanup()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")