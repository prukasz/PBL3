from abc import ABC, abstractmethod
import asyncio
import subprocess
import struct
import paho.mqtt.client as mqtt

class MQTTInterface(ABC):
    def __init__(self, broker_address: str, broker_port: int):
        self.broker_address = broker_address
        self.broker_port = broker_port
                          
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def publish(self, topic: str, payload: str) -> bool:
        pass

    @abstractmethod
    async def subscribe(self, topic: str, payload: str) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        pass



class MQTTInterfacePaho(MQTTInterface):
    def __init__(self, broker_address: str, broker_port: int, on_message_callback):
        super().__init__(broker_address, broker_port)
        self.client = mqtt.Client(client_id="BeaconClient", clean_session=False)
        self.client.on_message = on_message_callback

    async def connect(self) -> bool:
        # Implement connection logic using Paho MQTT
        try:
            await asyncio.to_thread(
                self.client.connect, 
                self.broker_address, 
                self.broker_port, 
            )
            self.client.loop_start()  # Start network loop in background thread
            await asyncio.sleep(0.1)  # Give it moment to establish connection
            return True
        except Exception as e:
            print(f"[MQTT] Connection failed: {e}")
            return False
    
    async def publish(self, topic: str, payload: str, quality: int) -> bool:
        # Implement publish logic using Paho MQTT
        try:
            result = self.client.publish(topic, payload, qos=quality)
            # Wait for publish to complete (timeout 2 seconds)
            await asyncio.to_thread(result.wait_for_publish, timeout=2.0)
            return True
        except Exception as e:
            print(f"[MQTT] Publish failed: {e}")
            return False

    async def subscribe(self, topic: str, quality: int) -> bool:
        # Implement subscribe logic using Paho MQTT
        try:
            self.client.subscribe(topic, qos=quality)
            return True
        except Exception as e:
            print(f"[MQTT] Subscribe failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        # Implement disconnect logic using Paho MQTT
        try:
            self.client.loop_stop()  # Stop background loop
            await asyncio.to_thread(self.client.disconnect)
            return True
        except Exception as e:
            print(f"[MQTT] Disconnect failed: {e}")
            return False

