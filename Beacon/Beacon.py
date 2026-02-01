from Ble_conn import BLEInterface, BleakBLEInterface
from Wifi_conn import WifiInterface
from MQTT_conn import MQTTInterfaceBeacon
from Data_processing import BeaconDataProcessor
from pprint import pprint
import time
import asyncio
import subprocess


class Beacon:
    ALARM_REPEAT_COUNT = 3  # Number of cycles to repeat alarm
    
    def __init__(self, wifi_adapter: WifiInterface, ble_adapter: BLEInterface, data_processor: BeaconDataProcessor, mqtt_client: MQTTInterfaceBeacon, adv_time: int, adv_period: int, scan_time: int, loop=None):
        self.ble = ble_adapter
        self.processor = data_processor
        self.scan_time = scan_time
        self.adv_time = adv_time
        self.adv_period = adv_period
        self.wifi = wifi_adapter
        self.mqtt = mqtt_client
        self.loop = loop  # Event loop for MQTT callback from different thread
        
        self.alarm_queue = asyncio.Queue()  # Queue for incoming alarms
        self.current_alarm = None  # Track current alarm being processed (dict with payload and remaining)
        
        if hasattr(self.mqtt, 'client'):
            self.mqtt.client.on_message = self.on_message


    def get_bluetooth_mac(self) -> str:
        try: 
            cmd = subprocess.check_output(['hcitool', 'dev']).decode('utf-8')
            bluetooth_mac = (cmd.split()[2]).replace(":","")
            return bluetooth_mac
        except Exception as e:
            print(f"[Beacon] Error getting Bluetooth MAC: {e}")
            return "000000000000"  # Default/fallback MAC

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        print(f"[MQTT] Received message: {payload}")
        
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.add_alarm_to_queue(payload),
                self.loop
            )
        else:
            print("[Beacon] Warning: Event loop not set, cannot trigger advertising")
    
    async def add_alarm_to_queue(self, payload: str):
        if self.current_alarm and self.current_alarm['payload'] == payload:
            print(f"[Beacon] Alarm already being processed, ignoring: {payload}")
            return
        
        queue_items = list(self.alarm_queue._queue)
        if any(item['payload'] == payload for item in queue_items):
            print(f"[Beacon] Alarm already in queue, ignoring: {payload}")
            return
        
        alarm_item = {'payload': payload, 'remaining': self.ALARM_REPEAT_COUNT}
        await self.alarm_queue.put(alarm_item)
        print(f"[Beacon] Alarm added to queue: {payload}, Queue size: {self.alarm_queue.qsize()})")

    async def run_cycle(self): 
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
        
        beacon_mac = self.get_bluetooth_mac()

        for dev in selected_tags:
            Topic = f"floor/{beacon_mac}/{dev['mac'].replace(":","")}"
            await self.mqtt.publish(Topic, ''.join(['' + data.hex() for data in dev['mdata'].values()]), 1)

        if self.current_alarm is None and not self.alarm_queue.empty():
            self.current_alarm = await self.alarm_queue.get()
            print(f"[Beacon] Starting new alarm: {self.current_alarm['payload']} ({self.current_alarm['remaining']} cycles)")

        if self.current_alarm is not None:
            payload = self.current_alarm['payload']
            remaining = self.current_alarm['remaining']

            formatted_payload = self.processor.get_alarm_payload(payload)
            print(f"[Beacon] Advertising alarm: {payload} (cycle {self.ALARM_REPEAT_COUNT - remaining + 1}/{self.ALARM_REPEAT_COUNT})")

            success = await self.ble.advertise(
                time=self.adv_time, 
                period=self.adv_period, 
                payload=formatted_payload
            )
            
            if success:
                print(f"[Beacon] Alarm advertising finished successfully: {payload}")
                self.current_alarm['remaining'] -= 1
                if self.current_alarm['remaining'] <= 0:
                    print(f"[Beacon] Alarm completed all {self.ALARM_REPEAT_COUNT} cycles: {payload}")
                    self.current_alarm = None
                else:
                    print(f"[Beacon] Alarm will continue: {payload} ({self.current_alarm['remaining']} cycles remaining)")
            else:
                print(f"[Beacon] Alarm advertising failed: {payload}, will retry next cycle")
            return
        else:
            print("[Beacon] No alarms in queue, advertising hollow package for rssi")
            payload = ""
            formatted_payload = self.processor.get_alarm_payload(payload)
            print(f"[Beacon] Formatted payload: {formatted_payload}")
            success = await self.ble.advertise(
                time=self.adv_time, 
                period=self.adv_period, 
                payload=formatted_payload
            )
            if success:
                print(f"[Beacon] Hollow advertising finished successfully")
            else:
                print(f"[Beacon] Hollow advertising failed")


        