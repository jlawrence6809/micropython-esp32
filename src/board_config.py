import json
from instances import instances

class BoardConfig:
    """Board configuration manager for GPIO and hardware details."""
    
    def __init__(self):
        """Load board configuration from JSON file.
        
        Gets board file path from global config manager.
        """
        self.board_file = None
        self.config = {}
        self.load()
    
    def load(self):
        """Load board configuration from file."""
        # Get board file path from config manager
        self.board_file = instances.config.get_board_config_file()
        
        try:
            with open(self.board_file, 'r') as f:
                self.config = json.load(f)
            print(f"Loaded board config: {self.config.get('name', 'Unknown')}")
        except (OSError, ValueError) as e:
            print(f"Failed to load board config from {self.board_file}: {e}")
            # Provide minimal fallback config
            self.config = {
                "name": "Unknown",
                "chip": "ESP32",
                "valid_gpio_pins": [],
                "reserved_pins": []
            }
    
    def get_name(self):
        """Get human-readable board name."""
        return self.config.get('name', 'Unknown Board')
    
    def get_chip(self):
        """Get chip type."""
        return self.config.get('chip', 'ESP32')
    
    def get_valid_gpio_pins(self):
        """Get list of valid GPIO pins."""
        return self.config.get('valid_gpio_pins', [])
    
    def get_reserved_pins(self):
        """Get list of reserved GPIO pins."""
        return self.config.get('reserved_pins', [])
    
    def get_available_pins(self, exclude_pins=None):
        """
        Get list of available GPIO pins (valid pins minus reserved and excluded).
        
        Args:
            exclude_pins: List of pins to exclude (e.g., already in use)
        
        Returns:
            List of available GPIO pin numbers
        """
        if exclude_pins is None:
            exclude_pins = []
        
        valid = set(self.get_valid_gpio_pins())
        reserved = set(self.get_reserved_pins())
        excluded = set(exclude_pins)
        
        available = valid - reserved - excluded
        return sorted(list(available))
    
    def is_pin_valid(self, pin):
        """Check if a pin number is valid for this board."""
        return pin in self.get_valid_gpio_pins()
    
    def is_pin_reserved(self, pin):
        """Check if a pin is reserved (should not be used)."""
        return pin in self.get_reserved_pins()
    
    def get_notes(self):
        """Get board-specific notes."""
        return self.config.get('notes', {})
    
    def get_default_sensor_pins(self):
        """Get default sensor pin configuration."""
        return self.config.get('default_sensor_pins', {})
    
    def get_i2c_config(self):
        """Get I2C pin configuration."""
        return self.config.get('i2c', {'scl': -1, 'sda': -1})

    def get_rgb_led_pin(self):
        """Get RGB LED pin configuration."""
        return self.config.get('rgb_led', -1)
    
    def get_clock_speed(self):
        """Get recommended CPU clock speed in Hz (e.g., 240000000 for 240 MHz)."""
        return self.config.get('clock_speed', None)
    
    def set_cpu_frequency(self):
        """Set CPU frequency from board configuration.
        
        Returns:
            True if frequency was set, False if using default
        """
        import machine
        
        try:
            clock_speed = self.get_clock_speed()
            if clock_speed:
                current_freq = machine.freq()
                if current_freq != clock_speed:
                    machine.freq(clock_speed)
                    print(f"✓ CPU frequency set to {clock_speed // 1_000_000} MHz (was {current_freq // 1_000_000} MHz)")
                else:
                    print(f"✓ CPU frequency already at {clock_speed // 1_000_000} MHz")
                return True
            else:
                print(f"✓ CPU frequency: {machine.freq() // 1_000_000} MHz (using default)")
                return False
        except Exception as e:
            print(f"⚠ Failed to set CPU frequency: {e}")
            return False
    
    def to_dict(self):
        """Return full configuration as dictionary."""
        return self.config.copy()

