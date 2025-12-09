from abc import ABC, abstractmethod
from Mqtt_conn import MqttConnection
import asyncio

class MqttReceiver(ABC):
    @property
    @abstractmethod
    def topic(self) -> str:
        """The topic this feature wants to listen to."""
        pass

    @abstractmethod
    async def handle_message(self, topic: str, payload: str):
        pass

class PremiumBeacon(MqttReceiver):
    
    @property
    def topic(self) -> str:
        return "floor/#"

    async def handle_message(self, topic: str, payload: str):
        print(f"{topic.removeprefix('floor/')}: {payload}") 

class MqttPublisher(ABC):
    @abstractmethod
    async def execute(self, mqtt_client: MqttConnection):
        """
        Run the publishing logic. 
        """
        pass

class AlarmTag(MqttPublisher):
    def __init__(self):
        self._queue = asyncio.Queue()

    async def trigger_alarm(self, topic_suffix: str, message: str): 
        await self._queue.put((topic_suffix, message))

    #this waits for new message in que put in trigger_alarm
    async def execute(self, mqtt_client: MqttConnection):
        while True:
            data = await self._queue.get()
            if not data or len(data) < 2:
                print(f"Error: Invalid alarm data received: {data}")
                self._queue.task_done()
                continue
            topic_suffix = data[0]
            message_content = data[1]
            full_topic = f"floor/{topic_suffix}"

            #Publish received content
            await mqtt_client.publish(full_topic, message_content)
            print(f"Sent: {full_topic} -> {message_content}")
            
            self._queue.task_done()


