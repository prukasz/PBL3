
import asyncio 
from Mqtt_interface import MqttInterface
from Mqtt_conn import PahoMQTTAdapter
from Mqtt_services import PremiumBeacon, AlarmTag

async def main():
    broker = PahoMQTTAdapter("192.168.1.19", 1883)

    #simple serivces to test
    beacon_handling = PremiumBeacon()
    alarm_service = AlarmTag()

    app = MqttInterface(
        mqtt_client=broker,
        features=[beacon_handling],      # Subscribers
        publishers=[alarm_service]       # Publishers
    )
  
    #run in backgroud
    interface_task = asyncio.create_task(app.start())

    while True:
        await alarm_service.trigger_alarm("Test2","Atakują")
        await alarm_service.trigger_alarm("Test1","Legia pany")
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass