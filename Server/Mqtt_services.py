from abc import ABC, abstractmethod
from Mqtt_conn import MqttConnection
from typing import List, Tuple
from pprint import pprint
import asyncio
from Radiomap import RadioMap 
# Import the Database Handler
from Database import InfluxHandler

class MqttReceiver(ABC):
    @property
    @abstractmethod
    def topic(self) -> str:
        """The topic this feature wants to listen to"""
        pass

    @abstractmethod
    async def handle_message(self, topic: str, payload: str):
        pass

class ReceiveFromBeacons(MqttReceiver):
    def __init__(self, radio_map: RadioMap, db_handler: InfluxHandler):
        """
        Dependency Injection: We ask for RadioMap AND Database Handler
        """
        self.radio_map = radio_map
        self.db = db_handler

    @property
    def topic(self) -> str:
        # Listening to floor/floor_x/MAC_ADDRESS
        return "floor/#"

    async def handle_message(self, topic: str, payload: str):
        # Calculate Position
        result = self.radio_map.get_position(payload)
    
        #Strip "floor/......" to get the clean MAC
        mac_address = topic[-12:]
        
        if result:
            x, y, label = result
            print(f"Received from {mac_address} -> Pos: ({x}, {y}), label {label}")
            
            # Write to InfluxDB
            self.db.write_position(mac_address, x, y)
        else:
            print(f"Received from {mac_address} -> Position calculation failed.")

class MqttPublisher(ABC):
    @abstractmethod
    async def execute(self, mqtt_client: MqttConnection):
        pass

class AlarmTag(MqttPublisher):
    def __init__(self):
        self._queue = asyncio.Queue()

    async def trigger_alarm(self, topic_suffix: str, message: str): 
        await self._queue.put((topic_suffix, message))

    async def execute(self, mqtt_client: MqttConnection):
        while True:
            data = await self._queue.get()
            if not data or len(data) < 2:
                self._queue.task_done()
                continue
            topic_suffix = data[0]
            message_content = data[1]
            full_topic = f"alarm/{topic_suffix}"

            await mqtt_client.publish(full_topic, message_content)
            print(f"Sent: {full_topic} -> {message_content}")      
            self._queue.task_done()