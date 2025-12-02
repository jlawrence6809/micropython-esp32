from instances import instances
from machine import Pin
import uasyncio as asyncio
from neopixel import NeoPixel

class BoardRgbLed:
    """Manages the onboard RGB LED with various states and effects."""
    
    # State definitions: (color, effect)
    STATES = {
        'booting': ((128, 0, 128), 'solid'),           # Purple - System initializing
        'ap_mode': ((255, 165, 0), 'breathe'),         # Orange - Hosting WiFi AP
        'normal': ((0, 255, 0), 'breathe'),            # Green breathing - Normal operation
        'warning': ((255, 255, 0), 'blink'),           # Yellow blinking - Warning/error
        'error': ((255, 0, 0), 'solid'),               # Red solid - Critical error
    }
    
    def __init__(self):
        self.rgb_led_pin = instances.board.get_rgb_led_pin()
        self.np = None
        self.current_state = 'off'
        self.current_color = (0, 0, 0)
        self.current_effect = 'solid'
        self._running = False
        
        # Initialize NeoPixel if pin is configured
        if self.rgb_led_pin != -1:
            try:
                pin = Pin(self.rgb_led_pin, Pin.OUT)
                self.np = NeoPixel(pin, 1)
                print(f"✓ RGB LED initialized on GPIO {self.rgb_led_pin}")
            except Exception as e:
                print(f"⚠ Failed to initialize RGB LED: {e}")
                self.np = None
        else:
            print("⚠ RGB LED pin not configured")
    
    def set_state(self, state_name):
        """Set LED state by name.
        
        Args:
            state_name: One of the predefined states (e.g., 'wifi_connecting', 'normal')
        """
        if state_name in self.STATES:
            color, effect = self.STATES[state_name]
            self.current_state = state_name
            self.current_color = color
            self.current_effect = effect
        else:
            print(f"⚠ Unknown LED state: {state_name}")
    
    def set_color(self, r, g, b, effect='solid'):
        """Set custom LED color and effect.
        
        Args:
            r, g, b: RGB values (0-255)
            effect: 'solid', 'blink', or 'breathe'
        """
        self.current_state = 'custom'
        self.current_color = (r, g, b)
        self.current_effect = effect
    
    def _write_color(self, r, g, b):
        """Write color to NeoPixel hardware."""
        if self.np:
            try:
                self.np[0] = (r, g, b)
                self.np.write()
            except Exception as e:
                print(f"⚠ Error writing to RGB LED: {e}")
    
    def _apply_brightness(self, color, brightness):
        """Scale RGB color by brightness factor.
        
        Args:
            color: (r, g, b) tuple
            brightness: 0-255
            
        Returns:
            Scaled (r, g, b) tuple
        """
        r, g, b = color
        factor = brightness / 255
        return (int(r * factor), int(g * factor), int(b * factor))
    
    async def _blink(self):
        """Blink effect: on for 500ms, off for 500ms."""
        # On
        self._write_color(*self.current_color)
        await asyncio.sleep(0.5)
        
        # Off
        self._write_color(0, 0, 0)
        await asyncio.sleep(0.5)
    
    async def _breathe(self):
        """Breathing effect: smooth fade in and out over ~2 seconds."""
        # Fade in (0 to 255 brightness)
        for brightness in range(0, 256, 10):
            scaled_color = self._apply_brightness(self.current_color, brightness)
            self._write_color(*scaled_color)
            await asyncio.sleep(0.02)
        
        # Fade out (255 to 0 brightness)
        for brightness in range(255, -1, -10):
            scaled_color = self._apply_brightness(self.current_color, brightness)
            self._write_color(*scaled_color)
            await asyncio.sleep(0.02)
    
    async def _solid(self):
        """Solid effect: just keep the color steady."""
        self._write_color(*self.current_color)
        await asyncio.sleep(1)  # Check for state changes every second
    
    async def run(self):
        """Main LED manager loop. Run this as an async task."""
        if not self.np:
            print("⚠ RGB LED not available, manager loop exiting")
            return
        
        self._running = True
        print("✓ RGB LED manager started")
        
        try:
            while self._running:
                # Execute current effect
                if self.current_effect == 'blink':
                    await self._blink()
                elif self.current_effect == 'breathe':
                    await self._breathe()
                elif self.current_effect == 'solid':
                    await self._solid()
                else:
                    # Unknown effect, default to solid
                    await self._solid()
                    
        except Exception as e:
            print(f"⚠ RGB LED manager error: {e}")
            import sys
            sys.print_exception(e)
    
    def stop(self):
        """Stop the LED manager loop."""
        self._running = False
        if self.np:
            self._write_color(0, 0, 0)  # Turn off LED