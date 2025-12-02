"""
Sensor management module for reading hardware sensors.

This module provides a unified interface for reading various sensors:
- Temperature/Humidity (AHT21 via I2C)
- Temperature (DS18B20 via OneWire)
- Light level (analog photo sensor via ADC)
- Switch state (digital input)

Sensor pins are configured via config.json (not board config).
All pins default to -1 (disabled) until explicitly configured.
"""

import time
from machine import Pin, ADC
from instances import instances

class SensorManager:
    """Manages all sensor readings with caching and throttling."""
    
    def __init__(self):
        # Current sensor values
        self.temperature = None  # Celsius
        self.humidity = None     # Percentage
        self.light_level = None  # 0-4095 (ADC range), None if not configured
        self.switch_state = False
        self.reset_switch_state = False
        
        # Last sensor values (for edge detection)
        self.last_temperature = None
        self.last_humidity = None
        self.last_light_level = None
        self.last_switch_state = False
        self.last_reset_switch_state = False
        self.last_time_seconds = 0  # For time-based edge detection
        
        # Timestamps for throttling
        self.last_temp_humidity_read = 0
        self.last_light_read = 0
        self.last_switch_read = 0
        
        # Read intervals (milliseconds)
        self.temp_humidity_interval = 2000  # 2 seconds (AHT21 reads both at once)
        self.light_interval = 500           # 500ms for photo sensor
        self.switch_interval = 50           # 50ms for debouncing
        
        # Hardware references
        self.aht21 = None
        self.ds18b20 = None
        self.ds18b20_rom = None
        self.photo_sensor_adc = None
        self.light_switch_pin = None
        self.reset_switch_pin = None
        
        self._init_hardware()
        
    def _init_hardware(self):
        """Initialize hardware sensors based on config.json sensor_pins."""
        # Get sensor pins from config manager
        sensor_pins = instances.config.get_sensor_pins()
        
        i2c_scl = sensor_pins.get('i2c_scl', -1)
        i2c_sda = sensor_pins.get('i2c_sda', -1)
        ds18b20_pin = sensor_pins.get('ds18b20', -1)
        photo_sensor_pin = sensor_pins.get('photo_sensor', -1)
        light_switch_pin = sensor_pins.get('light_switch', -1)
        reset_switch_pin = sensor_pins.get('reset_switch', -1)
        
        # Initialize AHT21 (temperature/humidity sensor via I2C)
        if i2c_scl != -1 and i2c_sda != -1:
            try:
                from aht21 import AHT21
                self.aht21 = AHT21(i2c_scl, i2c_sda)
                if self.aht21.Is_Calibrated():
                    print(f"✓ AHT21 sensor initialized (SCL={i2c_scl}, SDA={i2c_sda})")
                else:
                    print("⚠ AHT21 sensor not calibrated")
                    self.aht21 = None
            except Exception as e:
                print(f"⚠ Failed to initialize AHT21: {e}")
                self.aht21 = None
        
        # Initialize DS18B20 (one-wire temperature sensor)
        if ds18b20_pin != -1:
            try:
                import onewire
                import ds18x20
                ow = onewire.OneWire(Pin(ds18b20_pin))
                self.ds18b20 = ds18x20.DS18X20(ow)
                roms = self.ds18b20.scan()
                if roms:
                    self.ds18b20_rom = roms[0]  # Use first sensor found
                    print(f"✓ DS18B20 sensor initialized on GPIO {ds18b20_pin}")
                else:
                    print(f"⚠ No DS18B20 sensors found on GPIO {ds18b20_pin}")
                    self.ds18b20 = None
            except Exception as e:
                print(f"⚠ Failed to initialize DS18B20: {e}")
                self.ds18b20 = None
        
        # Initialize photo sensor (ADC)
        if photo_sensor_pin != -1:
            try:
                self.photo_sensor_adc = ADC(Pin(photo_sensor_pin))
                # Set 12-bit resolution (0-4095) and full voltage range
                self.photo_sensor_adc.atten(ADC.ATTN_11DB)
                print(f"✓ Photo sensor initialized on GPIO {photo_sensor_pin}")
            except Exception as e:
                print(f"⚠ Failed to initialize photo sensor: {e}")
                self.photo_sensor_adc = None
        
        # Initialize light switch (digital input with pullup)
        if light_switch_pin != -1:
            try:
                self.light_switch_pin = Pin(light_switch_pin, Pin.IN, Pin.PULL_UP)
                print(f"✓ Light switch initialized on GPIO {light_switch_pin}")
            except Exception as e:
                print(f"⚠ Failed to initialize light switch: {e}")
                self.light_switch_pin = None
        
        # Initialize reset switch (digital input with pullup)
        if reset_switch_pin != -1:
            try:
                self.reset_switch_pin = Pin(reset_switch_pin, Pin.IN, Pin.PULL_UP)
                print(f"✓ Reset switch initialized on GPIO {reset_switch_pin}")
            except Exception as e:
                print(f"⚠ Failed to initialize reset switch: {e}")
                self.reset_switch_pin = None
    
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
        """Read temperature and humidity from available sensors.
        
        Priority:
        1. AHT21 (I2C) - reads both temp and humidity
        2. DS18B20 (OneWire) - reads temp only, humidity stays None
        
        Returns:
            Tuple of (temperature_celsius, humidity_percent)
        """
        temp = None
        humidity = None
        
        # Try AHT21 first (gives both temp and humidity)
        if self.aht21:
            try:
                temp = self.aht21.T()       # Returns temperature in Celsius
                humidity = self.aht21.RH()  # Returns relative humidity %
            except Exception as e:
                print(f"⚠ Error reading AHT21: {e}")
        
        # If no temp yet, try DS18B20
        if temp is None and self.ds18b20 and self.ds18b20_rom:
            try:
                self.ds18b20.convert_temp()
                # DS18B20 needs ~750ms to convert, but we're called every 2s
                # so previous conversion should be ready
                temp = self.ds18b20.read_temp(self.ds18b20_rom)
            except Exception as e:
                print(f"⚠ Error reading DS18B20: {e}")
        
        return (temp, humidity)
    
    def _read_light_level(self):
        """Read light level from analog photo sensor.
        
        Returns:
            0-4095 (12-bit ADC value) or None if not configured
        """
        if self.photo_sensor_adc:
            try:
                return self.photo_sensor_adc.read()
            except Exception as e:
                print(f"⚠ Error reading photo sensor: {e}")
                return self.light_level  # Return last known value
        return None
    
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

