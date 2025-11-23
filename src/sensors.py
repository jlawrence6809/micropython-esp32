"""
Sensor management module for reading hardware sensors.

This module provides a unified interface for reading various sensors:
- Temperature (DS18B20)
- Humidity/Temperature (DHT22)
- Light level (analog photo sensor)
- Switch state (digital input)

For Phase 1, all sensors return dummy values for testing.
Real hardware implementations will be added in Phase 2.
"""

import time

class SensorManager:
    """Manages all sensor readings with caching and throttling."""
    
    def __init__(self):
        # Current sensor values
        self.temperature = 22.0  # Celsius
        self.humidity = 50.0     # Percentage
        self.light_level = 500   # 0-4095 (ADC range)
        self.switch_state = False
        
        # Last sensor values (for edge detection)
        self.last_temperature = 22.0
        self.last_humidity = 50.0
        self.last_light_level = 500
        self.last_switch_state = False
        
        # Timestamps for throttling
        self.last_temp_read = 0
        self.last_humidity_read = 0
        self.last_light_read = 0
        self.last_switch_read = 0
        
        # Read intervals (milliseconds)
        self.temp_interval = 2000      # 2 seconds
        self.humidity_interval = 2000  # 2 seconds
        self.light_interval = 10000    # 10 seconds
        self.switch_interval = 100     # 100ms for debouncing
        
    def update_all(self):
        """Update all sensors based on their intervals."""
        current_time = time.ticks_ms()
        
        # Update temperature
        if time.ticks_diff(current_time, self.last_temp_read) >= self.temp_interval:
            self.last_temperature = self.temperature
            self.temperature = self._read_temperature()
            self.last_temp_read = current_time
        
        # Update humidity
        if time.ticks_diff(current_time, self.last_humidity_read) >= self.humidity_interval:
            self.last_humidity = self.humidity
            self.humidity = self._read_humidity()
            self.last_humidity_read = current_time
        
        # Update light level
        if time.ticks_diff(current_time, self.last_light_read) >= self.light_interval:
            self.last_light_level = self.light_level
            self.light_level = self._read_light_level()
            self.last_light_read = current_time
        
        # Update switch state
        if time.ticks_diff(current_time, self.last_switch_read) >= self.switch_interval:
            self.last_switch_state = self.switch_state
            self.switch_state = self._read_switch_state()
            self.last_switch_read = current_time
    
    def _read_temperature(self):
        """Read temperature from DS18B20 sensor.
        
        Phase 1: Returns dummy value.
        Phase 2: Will read from actual hardware.
        """
        # Dummy: Simulate temperature varying slightly
        import random
        return 22.0 + random.uniform(-2.0, 2.0)
    
    def _read_humidity(self):
        """Read humidity from DHT22 sensor.
        
        Phase 1: Returns dummy value.
        Phase 2: Will read from actual hardware.
        """
        # Dummy: Simulate humidity varying slightly
        import random
        return 50.0 + random.uniform(-10.0, 10.0)
    
    def _read_light_level(self):
        """Read light level from analog photo sensor.
        
        Phase 1: Returns dummy value.
        Phase 2: Will read from ADC.
        """
        # Dummy: Simulate light varying
        import random
        return int(500 + random.uniform(-200, 200))
    
    def _read_switch_state(self):
        """Read digital switch state.
        
        Phase 1: Returns dummy value.
        Phase 2: Will read from GPIO.
        """
        # Dummy: Keep same state for now
        return self.switch_state
    
    def get_temperature(self):
        """Get current temperature in Celsius."""
        return self.temperature
    
    def get_humidity(self):
        """Get current humidity percentage."""
        return self.humidity
    
    def get_light_level(self):
        """Get current light level (0-4095)."""
        return self.light_level
    
    def get_switch_state(self):
        """Get current switch state (True/False)."""
        return self.switch_state
    
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
        """Get previous switch state."""
        return self.last_switch_state
    
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
            "time_seconds": self.get_time_seconds()
        }

