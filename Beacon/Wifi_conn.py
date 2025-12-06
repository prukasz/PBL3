from abc import ABC, abstractmethod
import asyncio
import subprocess
import struct

class WifiInterface(ABC):
    def __init__(self):
        self.adapter = "wlan0"  #default adapter name

    @abstractmethod
    async def connect_wifi(ssid, password):
        pass

class WifiConn(WifiInterface):
    async def connect_wifi(ssid, password):
    proc = await asyncio.create_subprocess_exec(
        'nmcli', 'device', 'wifi', 'connect', ssid, 'password', password,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.wait()
    return proc.returncode == 0