import asyncio 
from Mqtt_interface import MqttInterface
from Mqtt_conn import PahoMQTTAdapter
from Mqtt_services import ReceiveFromBeacons, AlarmTag
from Radiomap import BLERadioMap
from Database import InfluxHandler

async def main():
    #Temporary config 
    #ip są w ten sposób ponieważ używane było wiele różnch sieci
    MQTT_BROKER_IP = "192.168.114.74"
    MQTT_PORT = 1883
    DB_URL = "http://192.168.114.74:8086"
    DB_TOKEN = "HnJNerjV3H5ay1g8oPvyWqc6A3L4Rucl5SBjHZ8rRWC-8nJVKqeEMYjKB1qJ40Jwst8xvj05AdTCG6qTi2jNEQ=="
    DB_ORG = "PBL3"
    DB_BUCKET = "Position"

    #Initialize Adapters
    broker = PahoMQTTAdapter(MQTT_BROKER_IP, MQTT_PORT)
    
    #Initialize Database
    db_handler = InfluxHandler(DB_URL, DB_TOKEN, DB_ORG, DB_BUCKET)

    #Initialize Domain Logic
    radio_map = BLERadioMap()
    radio_map.load_data("radiomap.txt")
    
    #Services
    beacon_handling = ReceiveFromBeacons(radio_map, db_handler)
    alarm_service = AlarmTag()

    app = MqttInterface(
        mqtt_client=broker,
        features=[beacon_handling],      # Subscribers
        publishers=[alarm_service]       # Publishers
    )
  
    try:
        interface_task = asyncio.create_task(app.start())
        
        #Get current event loop
        loop = asyncio.get_running_loop()
        print("System started. Type 'alarm' to test")

        while True:
            # Run blocking 'input' in a separate thread so it doesn't freeze the app
            user_input = await loop.run_in_executor(None, input)
            

            #this is for debug/show purposes only
            if "alarm" in user_input.lower():
                print("Triggering Alarm")
                await alarm_service.trigger_alarm("alarm", "B827EB0F88D0FFDDFF")

    finally:
        db_handler.close()

if __name__ == "__main__":
    try:
         asyncio.run(main())
    except KeyboardInterrupt:
        pass