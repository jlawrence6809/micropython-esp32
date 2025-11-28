"""
Sensor management module for reading hardware sensors.

This module provides a unified interface for reading various sensors:
- Temperature/Humidity (AHT21 via I2C)
- Light level (analog photo sensor) - not yet implemented
- Switch state (digital input)
"""

import time
from machine import Pin
from instances import instances

class SensorManager:
    """Manages all sensor readings with caching and throttling."""
    
    def __init__(self):
        # Current sensor values
        self.temperature = None  # Celsius
        self.humidity = None     # Percentage
        self.light_level = 0     # 0-4095 (ADC range) - not implemented yet
        self.switch_state = False
        self.reset_switch_state = False
        
        # Last sensor values (for edge detection)
        self.last_temperature = None
        self.last_humidity = None
        self.last_light_level = 0
        self.last_switch_state = False
        self.last_reset_switch_state = False
        self.last_time_seconds = 0  # For time-based edge detection
        
        # Timestamps for throttling
        self.last_temp_humidity_read = 0
        self.last_light_read = 0
        self.last_switch_read = 0
        
        # Read intervals (milliseconds)
        self.temp_humidity_interval = 2000  # 2 seconds (AHT21 reads both at once)
        self.light_interval = 10000         # 10 seconds
        self.switch_interval = 50           # 50ms for debouncing
        
        # Hardware initialization
        self.aht21 = None
        self.light_switch_pin = None
        self.reset_switch_pin = None
        self._init_hardware()
        
    def _init_hardware(self):
        """Initialize hardware sensors based on board configuration."""
        try:
            # Get sensor pins from board config
            sensor_pins = instances.board.get_default_sensor_pins()
            i2c_config = instances.board.get_i2c_config()
            
            # Initialize AHT21 (temperature/humidity sensor via I2C)
            if i2c_config['scl'] != -1 and i2c_config['sda'] != -1:
                try:
                    from AHT21 import AHT21
                    self.aht21 = AHT21(i2c_config['scl'], i2c_config['sda'])
                    if self.aht21.Is_Calibrated():
                        print("✓ AHT21 sensor initialized and calibrated")
                    else:
                        print("⚠ AHT21 sensor not calibrated")
                        self.aht21 = None
                except Exception as e:
                    print(f"⚠ Failed to initialize AHT21: {e}")
                    self.aht21 = None
            
            # Initialize light switch (digital input with pullup)
            light_switch_pin = sensor_pins.get('light_switch', -1)
            if light_switch_pin != -1:
                try:
                    self.light_switch_pin = Pin(light_switch_pin, Pin.IN, Pin.PULL_UP)
                    print(f"✓ Light switch initialized on GPIO {light_switch_pin}")
                except Exception as e:
                    print(f"⚠ Failed to initialize light switch: {e}")
                    self.light_switch_pin = None
            
            # Initialize reset switch (digital input with pullup)
            reset_switch_pin = sensor_pins.get('reset_switch', -1)
            if reset_switch_pin != -1:
                try:
                    self.reset_switch_pin = Pin(reset_switch_pin, Pin.IN, Pin.PULL_UP)
                    print(f"✓ Reset switch initialized on GPIO {reset_switch_pin}")
                except Exception as e:
                    print(f"⚠ Failed to initialize reset switch: {e}")
                    self.reset_switch_pin = None
            
        except Exception as e:
            print(f"⚠ Error initializing sensors: {e}")
    
    def update_all(self):
        """Update all sensors based on their intervals."""
        current_time = time.ticks_ms()
        
        # Update time (always, for edge detection)
        self.last_time_seconds = self.get_time_seconds()
        
        # Update temperature and humidity (AHT21 reads both at once)
        if time.ticks_diff(current_time, self.last_temp_humidity_read) >= self.temp_humidity_interval:
            self.last_temperature = self.temperature
            self.last_humidity = self.humidity
            temp, humidity = self._read_temp_humidity()
            self.temperature = temp
            self.humidity = humidity
            self.last_temp_humidity_read = current_time
        
        # Update light level (not implemented yet)
        if time.ticks_diff(current_time, self.last_light_read) >= self.light_interval:
            self.last_light_level = self.light_level
            self.light_level = self._read_light_level()
            self.last_light_read = current_time
        
        # Update switch states
        if time.ticks_diff(current_time, self.last_switch_read) >= self.switch_interval:
            self.last_switch_state = self.switch_state
            self.last_reset_switch_state = self.reset_switch_state
            self.switch_state = self._read_switch_state()
            self.reset_switch_state = self._read_reset_switch_state()
            self.last_switch_read = current_time
    
    def _read_temp_humidity(self):
        """Read temperature and humidity from AHT21 sensor.
        
        Returns:
            Tuple of (temperature_celsius, humidity_percent)
        """
        if self.aht21:
            try:
                temp = self.aht21.T()      # Returns temperature in Celsius
                humidity = self.aht21.RH()  # Returns relative humidity %
                return (temp, humidity)
            except Exception as e:
                print(f"⚠ Error reading AHT21: {e}")
                # Return last known values on error
                return (self.temperature if self.temperature is not None else 22.0,
                        self.humidity if self.humidity is not None else 50.0)
        else:
            # No sensor available, return None
            return (None, None)
    
    def _read_light_level(self):
        """Read light level from analog photo sensor.
        
        Not yet implemented - returns 0.
        """
        # TODO: Implement ADC reading for photo sensor
        return 0
    
    def _read_switch_state(self):
        """Read light switch state (active low with pullup).
        
        Returns True when switch is pressed (pin reads LOW).
        """
        if self.light_switch_pin:
            try:
                # Pin is pulled up, so 0 = pressed, 1 = not pressed
                return self.light_switch_pin.value() == 0
            except Exception as e:
                print(f"⚠ Error reading light switch: {e}")
                return False
        return False
    
    def _read_reset_switch_state(self):
        """Read reset switch state (active low with pullup).
        
        Returns True when switch is pressed (pin reads LOW).
        """
        if self.reset_switch_pin:
            try:
                # Pin is pulled up, so 0 = pressed, 1 = not pressed
                return self.reset_switch_pin.value() == 0
            except Exception as e:
                print(f"⚠ Error reading reset switch: {e}")
                return False
        return False
    
    def get_temperature(self):
        """Get current temperature in Celsius (or None if not available)."""
        return self.temperature
    
    def get_humidity(self):
        """Get current humidity percentage (or None if not available)."""
        return self.humidity
    
    def get_light_level(self):
        """Get current light level (0-4095)."""
        return self.light_level
    
    def get_switch_state(self):
        """Get current light switch state (True when pressed)."""
        return self.switch_state
    
    def get_reset_switch_state(self):
        """Get current reset switch state (True when pressed)."""
        return self.reset_switch_state
    
    def get_last_temperature(self):
        """Get previous temperature reading."""
        return self.last_temperature
    
    def get_last_humidity(self):
        """Get previous humidity reading."""
        return self.last_humidity
    
    def get_last_light_level(self):
        """Get previous light level reading."""
        return self.last_light_level
    
    def get_last_switch_state(self):
        """Get previous light switch state."""
        return self.last_switch_state
    
    def get_last_reset_switch_state(self):
        """Get previous reset switch state."""
        return self.last_reset_switch_state
    
    def get_last_time(self):
        """Get previous time reading (seconds since midnight).
        
        Useful for detecting time-based edges (e.g., crossing 8 PM).
        """
        return self.last_time_seconds
    
    def get_time_seconds(self):
        """Get current time as seconds since midnight.
        
        Returns uptime % 86400 if RTC not set, otherwise actual time.
        """
        try:
            import time
            # Try to get actual time if RTC is set
            t = time.localtime()
            return t[3] * 3600 + t[4] * 60 + t[5]  # hour*3600 + min*60 + sec
        except:
            # Fallback: use uptime modulo 24 hours
            return (time.ticks_ms() // 1000) % 86400
    
    def to_dict(self):
        """Return all sensor values as a dictionary (for API)."""
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "light_level": self.light_level,
            "switch_state": self.switch_state,
            "reset_switch_state": self.reset_switch_state,
            "time_seconds": self.get_time_seconds()
        }

