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
        
        # Alarm queue system
        self.alarm_queue = asyncio.Queue()  # Queue for incoming alarms
        self.current_alarm = None  # Track current alarm being processed
        self.is_processing_alarm = False  # Flag to prevent overlapping alarm processing
        
        # Set this instance's on_message as MQTT callback
        if hasattr(self.mqtt, 'client'):
            self.mqtt.client.on_message = self.on_message

    def on_message(self, client, userdata, msg):
        """Callback wywoływany przez MQTT - przetwarza wiadomość"""
        payload = msg.payload.decode()
        print(f"[MQTT] Received message: {payload}")
        
        if self.loop:
            # Add alarm to queue instead of triggering immediately
            asyncio.run_coroutine_threadsafe(
                self.add_alarm_to_queue(payload),
                self.loop
            )
        else:
            print("[Beacon] Warning: Event loop not set, cannot trigger advertising")
    
    async def add_alarm_to_queue(self, payload: str):
        """Add alarm to queue with deduplication"""
        # Check if this alarm is already in the queue or being processed
        if self.current_alarm == payload:
            print(f"[Beacon] Alarm already being processed, ignoring: {payload}")
            return
        
        # Check if alarm is already in queue (peek at queue items)
        queue_items = list(self.alarm_queue._queue)
        if payload in queue_items:
            print(f"[Beacon] Alarm already in queue, ignoring: {payload}")
            return
        
        await self.alarm_queue.put(payload)
        print(f"[Beacon] Alarm added to queue: {payload} (Queue size: {self.alarm_queue.qsize()})")
    
    async def process_alarm_queue(self):
        """Continuously process alarms from the queue one at a time"""
        print("[Beacon] Alarm queue processor started")
        
        while True:
            try:
                # Wait for an alarm from the queue
                payload = await self.alarm_queue.get()
                
                # Set current alarm and processing flag
                self.current_alarm = payload
                self.is_processing_alarm = True
                
                print(f"[Beacon] Processing alarm from queue: {payload}")
                
                # Set flag to pause run_cycle
                self.mqtt_advertising_active = True
                
                # Wait for scanning to finish if active (with timeout)
                wait_count = 0
                max_wait = 20  # Maximum 10 seconds (20 * 0.5s)
                while BleakBLEInterface._is_scanning and wait_count < max_wait:
                    print("[Beacon] Waiting for scan to finish...")
                    await asyncio.sleep(0.5)
                    wait_count += 1
                
                if wait_count >= max_wait:
                    print("[Beacon] Warning: Timeout waiting for scan to finish")
                
                # Perform advertising
                success = await self.ble.advertise(
                    time=self.adv_time, 
                    period=self.adv_period, 
                    payload=payload
                )
                
                if success:
                    print(f"[Beacon] Alarm advertising finished successfully: {payload}")
                else:
                    print(f"[Beacon] Alarm advertising failed: {payload}")
                
                # Clear flags
                self.mqtt_advertising_active = False
                self.current_alarm = None
                self.is_processing_alarm = False
                
                # Mark task as done
                self.alarm_queue.task_done()
                
            except Exception as e:
                print(f"[Beacon] Error processing alarm: {e}")
                self.mqtt_advertising_active = False
                self.current_alarm = None
                self.is_processing_alarm = False

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

        for dev in selected_tags:
            Topic = f"floor/{bluetooth_mac}/{dev['mac'].replace(":","")}"
            await self.mqtt.publish(Topic, ''.join(['' + data.hex() for data in dev['mdata'].values()]), 1)
        