import board
import asyncio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from BuzzerHandler import BuzzerHandler


class OLEDDisplay:
    WIDTH = 128
    HEIGHT = 64
    BORDER = 5
    
    def __init__(self, width=128, height=64, i2c_address=0x3C, alarm_duration=3.0):

        self.width = width
        self.height = height
        self.alarm_duration = alarm_duration
        
        i2c = board.I2C()
        self.oled = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=i2c_address)
        
        self.font = ImageFont.load_default(size=18)

        self.clear()
        
    def clear(self):
        self.oled.fill(0)
        self.oled.show()
        
    def _get_font_size(self, text):

        left, top, right, bottom = self.font.getbbox(text)
        return right - left, bottom - top
    
    def _create_alarm_image(self, text):

        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        draw.rectangle((0, 0, self.width, self.height), outline=255, fill=255)
        
        draw.rectangle(
            (self.BORDER, self.BORDER, 
             self.width - self.BORDER - 1, 
             self.height - self.BORDER - 1),
            outline=0,
            fill=0,
        )
        
        lines = self._wrap_text(text)
        
        line_heights = [self._get_font_size(line)[1] for line in lines]
        total_height = sum(line_heights) + (len(lines) - 1) * 2

        y_position = (self.height - total_height) // 2

        for line in lines:
            font_width, font_height = self._get_font_size(line)
            x_position = (self.width - font_width) // 2
            draw.text(
                (x_position, y_position),
                line,
                font=self.font,
                fill=255,
            )
            y_position += font_height + 2
        
        return image
    
    def _wrap_text(self, text, max_width=None):
        if max_width is None:
            max_width = self.width - 2 * self.BORDER - 4
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            line_width = self._get_font_size(test_line)[0]
            
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    async def show_alarm(self, message, buzzer=None):
        image = self._create_alarm_image(message)
        
        self.oled.image(image)
        self.oled.show()
        
        if buzzer:
            await buzzer.alarm_pattern(beeps=10)
        
        await asyncio.sleep(self.alarm_duration)
        self.clear()

