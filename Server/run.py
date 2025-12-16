import asyncio 
from Mqtt_interface import MqttInterface
from Mqtt_conn import PahoMQTTAdapter
from Mqtt_services import ReceiveFromBeacons, AlarmTag
from Radiomap import BLERadioMap
from Database import InfluxHandler

async def main():
    # --- Configuration ---
    #MQTT_BROKER_IP = "192.168.114.74"
    MQTT_BROKER_IP = "10.242.193.176"
    #DB_URL = "http://192.168.114.74:8086"
    DB_URL = "http://10.242.193.176:8086"
    DB_TOKEN = "HnJNerjV3H5ay1g8oPvyWqc6A3L4Rucl5SBjHZ8rRWC-8nJVKqeEMYjKB1qJ40Jwst8xvj05AdTCG6qTi2jNEQ=="
    DB_ORG = "PBL3"
    DB_BUCKET = "Position"

    # 1. Initialize Adapters
    broker = PahoMQTTAdapter(MQTT_BROKER_IP, 1883)
    
    # 2. Initialize Database
    db_handler = InfluxHandler(DB_URL, DB_TOKEN, DB_ORG, DB_BUCKET)

    # 3. Initialize Domain Logic
    radio_map = BLERadioMap()
    radio_map.load_data("scan_results2.txt")
    
    # 4. Initialize Services (Inject Dependencies)
    beacon_handling = ReceiveFromBeacons(radio_map, db_handler)
    alarm_service = AlarmTag()

    app = MqttInterface(
        mqtt_client=broker,
        features=[beacon_handling],      # Subscribers
        publishers=[alarm_service]       # Publishers
    )
  
    try:
        interface_task = asyncio.create_task(app.start())
        await interface_task
    finally:
        # Ensure database closes cleanly on exit
        db_handler.close()

if __name__ == "__main__":
    try:
         asyncio.run(main())
    except KeyboardInterrupt:
        pass