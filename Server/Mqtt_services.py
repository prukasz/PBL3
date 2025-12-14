from abc import ABC, abstractmethod
from Mqtt_conn import MqttConnection
from typing import List, Tuple
from pprint import pprint
import asyncio
# Import the interface, not the concrete implementation
from Radiomap import RadioMap 

class MqttReceiver(ABC):
    @property
    @abstractmethod
    def topic(self) -> str:
        """The topic this feature wants to listen to."""
        pass

    @abstractmethod
    async def handle_message(self, topic: str, payload: str):
        pass

class ReceiveFromBeacons(MqttReceiver):
    def __init__(self, radio_map: RadioMap):
        """
        Dependency Injection: We ask for a RadioMap class in the constructor.
        The map should already be loaded.
        """
        self.radio_map = radio_map

    @property
    def topic(self) -> str:
        return "floor/#"

    async def handle_message(self, topic: str, payload: str):
        result = self.radio_map.get_position(payload)
        print(f"Received on {topic.strip('floor/')}, data: {payload}")
        pprint(result)

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