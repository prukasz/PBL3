from Ble_conn import BLEInterface, BleakBLEInterface
from Wifi_conn import WifiInterface
from MQTT_conn import MQTTInterface
from Data_processing import DataProcessor
from pprint import pprint
import time
import asyncio
import subprocess


class Beacon:
    def __init__(self, wifi_adapter: WifiInterface ,ble_adapter: BLEInterface, data_processor: DataProcessor, mqtt_client: MQTTInterface, adv_time: int, adv_period: int, scan_time: int, loop=None):
        self.ble = ble_adapter  # Dependency Injection
        self.processor = data_processor  # Dependency Injection
        self.scan_time = scan_time
        self.adv_time = adv_time
        self.adv_period = adv_period
        self.wifi = wifi_adapter  # Dependency Injection
        self.mqtt = mqtt_client  # Dependency Injection
        self.mqtt_advertising_active = False  # Flag to pause run_cycle during MQTT advertising
        self.loop = loop  # Event loop for MQTT callback from different thread
        
        # Set this instance's on_message as MQTT callback
        if hasattr(self.mqtt, 'client'):
            self.mqtt.client.on_message = self.on_message

    def on_message(self, client, userdata, msg):
        """Callback wywoływany przez MQTT - przetwarza wiadomość"""
        payload = msg.payload.decode()
        print(f"[MQTT] Received message: {payload}")
        
        if self.loop:
            # MQTT callback działa w osobnym wątku, musimy użyć run_coroutine_threadsafe
            asyncio.run_coroutine_threadsafe(
                self.advertise_from_mqtt(payload),
                self.loop
            )
        else:
            print("[Beacon] Warning: Event loop not set, cannot trigger advertising")
    
    async def advertise_from_mqtt(self, payload: str):
        """Trigger BLE advertising with payload from MQTT message"""
        print(f"[Beacon] Starting advertising from MQTT with payload: {payload}")
        
        # Set flag to pause run_cycle
        self.mqtt_advertising_active = True
        
        # Wait for scanning to finish if active
        while BleakBLEInterface._is_scanning:
            print("[Beacon] Waiting for scan to finish...")
            await asyncio.sleep(0.5)
        
        success = await self.ble.advertise(
            time=self.adv_time, 
            period=self.adv_period, 
            payload=payload
        )
        
        # Clear flag after advertising completes
        self.mqtt_advertising_active = False
        
        if success:
            print("[Beacon] MQTT-triggered advertising finished successfully")
        else:
            print("[Beacon] MQTT-triggered advertising failed")

    async def run_cycle(self):
        # Skip scanning if MQTT advertising is active
        if self.mqtt_advertising_active:
            await asyncio.sleep(0.5)
            return
        
        print(f"[Beacon] Scanning for {self.scan_time} seconds")
        raw_devices = await self.ble.scan(duration=self.scan_time)

        pprint(raw_devices)

        selected_tags = self.processor.get_tags(raw_devices)

        if selected_tags:
            print(f"[Beacon] Found {len(selected_tags)} compliant tags:")
            for dev in selected_tags:
                print(f"Filtered: {dev['mac']} ({dev['name']}) | Data: {''.join(['0x' + data.hex() for data in dev['mdata'].values()])}")
        else:
            print("[Beacon] No compliant tags found.")

        cmd = subprocess.check_output(['hcitool', 'dev']).decode('utf-8')

        # The output looks like "Devices:\n\thci0\tAA:BB:CC:DD:EE:FF", so we split it to get the address
        bluetooth_mac = (cmd.split()[2]).replace(":","")

        await self.mqtt.publish(bluetooth_mac, "TEST", 1)
        