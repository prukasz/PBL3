import RPi.GPIO as GPIO
import asyncio
import atexit


class BuzzerHandler:
    def __init__(self, pin=18):
        self.pin = pin
        self._cleaned_up = False
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        
        atexit.register(self.cleanup)
    
    async def alarm_pattern(self, beeps=3, on_time=0.3, off_time=0.2):
        for _ in range(beeps):
            GPIO.output(self.pin, GPIO.HIGH)
            await asyncio.sleep(on_time)
            GPIO.output(self.pin, GPIO.LOW)
            await asyncio.sleep(off_time)
    
    def cleanup(self):
        if self._cleaned_up:
            return
        self._cleaned_up = True
        try:
            GPIO.output(self.pin, GPIO.LOW)
            GPIO.cleanup(self.pin)
        except Exception:
            pass  
