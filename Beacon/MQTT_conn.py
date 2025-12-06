from abc import ABC, abstractmethod
import asyncio
import subprocess
import struct

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