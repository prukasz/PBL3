import asyncio
import paho.mqtt.client as mqtt
from typing import Callable, Any
from abc import ABC, abstractmethod


#callbac structure
MessageCallback = Callable[[str, str], Any]

class MqttConnection(ABC):
    def __init__(self, broker_address: str, broker_port: int):
        self.broker_address = broker_address
        self.broker_port = broker_port

    @abstractmethod
    async def connect(self) -> bool: pass
    @abstractmethod
    async def publish(self, topic: str, payload: str) -> bool: pass
    @abstractmethod
    async def subscribe(self, topic: str, callback: MessageCallback) -> bool: pass
    @abstractmethod
    async def disconnect(self) -> bool: pass


#Using paho mqtt
class PahoMQTTAdapter(MqttConnection):
    def __init__(self, broker_address: str, broker_port: int, client_id: str = ""):
        super().__init__(broker_address, broker_port)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self._loop = None 

    async def connect(self) -> bool:
        self._loop = asyncio.get_running_loop()
        try:
            await self._loop.run_in_executor(None, self._blocking_connect)
            
            # Start Paho    
            self.client.loop_start()
            print(f"[PahoMQTTAdapter] Connected to {self.broker_address}")
            return True
        except Exception as e:
            print(f"[PahoMQTTAdapter]Connection failed: {e}")
            return False

    def _blocking_connect(self):
        self.client.connect(self.broker_address, self.broker_port, keepalive=60)

    async def publish(self, topic: str, payload: str) -> bool:
        try:
            # publish
            publish = self.client.publish(topic, payload)
            # Wait to complete
            publish.wait_for_publish(timeout=2) 
            return publish.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"[PahoMQTTAdapter]Publish error: {e}")
            return False

    async def subscribe(self, topic: str, callback: MessageCallback) -> bool:
        if not self._loop:
            print("[PahoMQTTAdapter] Error: Event loop not captured")
            return False

        def paho_thread_wrapper(client, userdata, message):
            payload_decoded = message.payload.decode('utf-8')
            
            
            asyncio.run_coroutine_threadsafe(
                callback(message.topic, payload_decoded), 
                self._loop
            )

        # Register the wrapper with Paho
        self.client.message_callback_add(topic, paho_thread_wrapper)
       
        result, _ = self.client.subscribe(topic)
        if result == mqtt.MQTT_ERR_SUCCESS:
            print(f"[PahoMQTTAdapter]Subscribed to topic: '{topic}'")
            return True
        return False

    async def disconnect(self) -> bool:
        self.client.loop_stop() 
        self.client.disconnect()
        print("[PahoMQTTAdapter] Disconnected")
        return True