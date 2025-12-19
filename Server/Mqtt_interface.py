import asyncio
from typing import List
from Mqtt_conn import MqttConnection
from Mqtt_services import MqttReceiver, MqttPublisher 

class MqttInterface:
    def __init__(self, mqtt_client: MqttConnection, features: List[MqttReceiver] = [], publishers: List[MqttPublisher] = []): 
        
        self.mqtt = mqtt_client
        self.features = features
        self.publishers = publishers

    async def start(self):    
        success = await self.mqtt.connect()
        if not success:
            return
        
        print("[MqttInterface] Setting up receivers")
        for feature in self.features:
            #pass topic and callback
            await self.mqtt.subscribe(feature.topic, feature.handle_message)
            print(f"Listening: {feature.__class__.__name__} on {feature.topic}")

        print("[MqttInterface] Setting up publishers")
        for pub in self.publishers:
            #each publish service will have own task in background
            asyncio.create_task(pub.execute(self.mqtt))
            print(f"[MqttInterface] Publishing {pub.__class__.__name__}")

        #DEBUG Tell that server is online
        await self.mqtt.publish("Server/status", "Server Online")

        while True:
            await asyncio.sleep(1)