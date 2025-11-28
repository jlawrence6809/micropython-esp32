from instances import instances
from machine import Pin
from time import sleep
from neopixel import NeoPixel

class BoardRgbLed:
    def __init__(self):
        self.rgb_led = instances.board.get_rgb_led_pin()

    def set_color(self, r, g, b):
        if (self.rgb_led == -1):
            print("RGB LED pin not configured")
            return
        try:
            pin = Pin(self.rgb_led, Pin.OUT)
            np = NeoPixel(pin, 1)
            np[0] = (r, g, b)
            np.write()
        except Exception as e:
            print(f"Error setting RGB LED color: {e}")