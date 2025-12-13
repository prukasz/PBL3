import asyncio
from Ble_conn import BleakBLEInterface
from Wifi_conn import WifiConn
from MQTT_conn import MQTTInterfacePaho
from Data_processing import DataFilterBeacon
from Beacon import Beacon


async def main():

    #custom uuid whitelist
    TARGET_MACS = [
        "C0:1A:14:25:CB:9B",
        "75:AE:8B:09:53:E9"
    ]
    
    SCAN_DURATION = 4
    ADV_DURATION = 1
    ADV_PERIOD_MS = 200

    try:
        loop = asyncio.get_running_loop()
        
        ble_interface = BleakBLEInterface()
        data_filter = DataFilterBeacon(target_macs=TARGET_MACS)
        wifi_interface = WifiConn()
        mqtt_interface = MQTTInterfacePaho(broker_address="192.168.114.74", broker_port=1883, on_message_callback=None)

        beacon = Beacon(
            ble_adapter=ble_interface, #DI
            data_processor=data_filter, #DI
            scan_time=SCAN_DURATION,
            adv_time=ADV_DURATION,
            adv_period=ADV_PERIOD_MS,
            wifi_adapter=wifi_interface,
            mqtt_client=mqtt_interface,
            loop=loop  # Przekaż event loop
        )

        await beacon.mqtt.connect()
        await beacon.mqtt.subscribe("alarm/#", 1)
        print("[main] Subscribed to alarm")
          
        # Start the alarm queue processor as a background task
        alarm_processor_task = asyncio.create_task(beacon.process_alarm_queue())
        print("[main] Alarm queue processor started")
        
        while True:        #run in loop
            await beacon.run_cycle()

    except Exception as e:
        print(f"[main], error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")