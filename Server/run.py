import asyncio 
from Mqtt_interface import MqttInterface
from Mqtt_conn import PahoMQTTAdapter
from Mqtt_services import ReceiveFromBeacons, AlarmTag
from Radiomap import BLERadioMap

async def main():
    broker = PahoMQTTAdapter("192.168.1.19", 1883)
    radio_map = BLERadioMap()
    radio_map.load_data("scan_results_old.txt")
    beacon_handling = ReceiveFromBeacons(radio_map)
    alarm_service = AlarmTag()

    app = MqttInterface(
        mqtt_client=broker,
        features=[beacon_handling],      # Subscribers
        publishers=[alarm_service]       # Publishers
    )
  
    interface_task = asyncio.create_task(app.start())
    await interface_task

if __name__ == "__main__":
    try:
         asyncio.run(main())
    except KeyboardInterrupt:
        pass