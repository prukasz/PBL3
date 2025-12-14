import asyncio
from Ble_conn import BleakBLEInterface
from Wifi_conn import WifiConn
from MQTT_conn import MQTTInterfacePaho
from Data_processing import BeaconDataFilter
from Beacon import Beacon


async def main():
    
    SCAN_DURATION = 4
    ADV_DURATION = 5
    ADV_PERIOD_MS = 200

    try:
        loop = asyncio.get_running_loop()
        
        ble_interface = BleakBLEInterface()
        data_filter = BeaconDataFilter()
        wifi_interface = WifiConn()
        mqtt_interface = MQTTInterfacePaho(broker_address="192.168.0.248", broker_port=1883, on_message_callback=None)

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

        while True:        #run in loop
            await beacon.run_cycle()

    except Exception as e:
        print(f"[main], error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")