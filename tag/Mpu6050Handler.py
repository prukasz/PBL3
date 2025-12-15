from mpu6050 import mpu6050
import RPi.GPIO as GPIO

class MpuHandler:
    def __init__(self, address=0x68, pin=17):
        self.address = address
        self.pin = pin
        self.sensor = None
        self.callback = None
        
        # Register Constants
        # Zgodnie z datasheet/innymi driverami
        self.REG_ACCEL_CONFIG = 0x1C 
        self.REG_MOT_THR      = 0x1F
        self.REG_MOT_DUR      = 0x20 
        self.REG_INT_PIN_CFG  = 0x37 
        self.REG_INT_ENABLE   = 0x38 
        self.REG_INT_STATUS   = 0x3A 

    def initialize(self):
        print(f"[MPU] Initializing on Pin {self.pin}...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        self.sensor = mpu6050(self.address)
        
        # Zgodnie z datasheet/innymi driverami
        self.sensor.bus.write_byte_data(self.address, self.REG_INT_PIN_CFG, 0x00)
        self.sensor.bus.write_byte_data(self.address, self.REG_INT_ENABLE, 0x00)
        self.sensor.bus.write_byte_data(self.address, self.REG_ACCEL_CONFIG, 0x01) # HPF 5Hz
        self.sensor.bus.write_byte_data(self.address, self.REG_MOT_THR, 15)        # Threshold
        self.sensor.bus.write_byte_data(self.address, self.REG_MOT_DUR, 40)        # Duration
        self.sensor.bus.write_byte_data(self.address, self.REG_INT_ENABLE, 0x40)
        print("[MPU] Hardware initialized.")

    def register_callback(self, callback_func):
        self.callback = callback_func

    def start_detection(self):
        try:
            #Clear any stuck interrupts on the MPU first
            self.sensor.bus.read_byte_data(self.address, self.REG_INT_STATUS)
            
            #Add GPIO event
            GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self._internal_interrupt_handler)
            print("[MPU] Listening for motion...")
        except Exception as e:
            print(f"[MPU] Failed to start detection: {e}")

    def stop_detection(self):
        try:
            GPIO.remove_event_detect(self.pin)
            print("[MPU] Paused")
        except:
            pass

    def _internal_interrupt_handler(self, channel):
        self.stop_detection()

        try:
            status = self.sensor.bus.read_byte_data(self.address, self.REG_INT_STATUS)
            if (status & 0x40) and self.callback:
                self.callback()
        except Exception as e:
            print(f"[MPU] Read error: {e}")
            self.start_detection()

    def cleanup(self):
        GPIO.cleanup()