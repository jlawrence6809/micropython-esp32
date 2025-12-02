import json

class ConfigManager:
    """Configuration manager using JSON file."""
    
    CONFIG_FILE = 'config.json'
    
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        """Load configuration from JSON file."""
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"Warning: Failed to load {self.CONFIG_FILE}: {e}")
            print("Using default configuration")
            return self._get_defaults()
    
    def _get_defaults(self):
        """Get default configuration."""
        return {
            "wifi": {
                "ssid": None,
                "password": None
            },
            "hostname": "esp32",
            "board": "unconfigured.json",
            "timezone": {
                "name": "UTC",
                "offset_seconds": 0
            }
        }
    
    def save_config(self):
        """Save configuration to JSON file."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                # MicroPython's json.dump doesn't support indent parameter
                json.dump(self.data, f)
            print(f"Configuration saved to {self.CONFIG_FILE}")
            return True
        except OSError as e:
            print(f"Failed to save configuration: {e}")
            return False
    
    # WiFi methods
    def get_wifi_ssid(self):
        return self.data.get('wifi', {}).get('ssid')
    
    def get_wifi_password(self):
        return self.data.get('wifi', {}).get('password')
    
    def set_wifi_credentials(self, ssid, password):
        """Set WiFi credentials (doesn't save automatically)."""
        if 'wifi' not in self.data:
            self.data['wifi'] = {}
        self.data['wifi']['ssid'] = ssid
        self.data['wifi']['password'] = password
    
    # Hostname methods
    def get_hostname(self):
        return self.data.get('hostname', 'esp32')
    
    def set_hostname(self, value):
        self.data['hostname'] = value
    
    # Board methods
    def get_board_filename(self):
        """Get board filename (e.g., 'esp32s3_devkitc_1_n16r8v.json')"""
        # Support legacy 'board_config' for migration
        if 'board' not in self.data and 'board_config' in self.data:
            # Convert old path format to filename
            old_path = self.data['board_config']
            if old_path:
                # Extract filename from path
                board_filename = old_path.split('/')[-1]
                self.data['board'] = board_filename
                del self.data['board_config']
                self.save_config()
        
        board = self.data.get('board', 'unconfigured.json')
        # Ensure it has .json extension
        if not board.endswith('.json'):
            board = f'{board}.json'
        return board
    
    def get_board_config_file(self):
        """Get full board config file path"""
        return f'/boards/{self.get_board_filename()}'
    
    def set_board_config_file(self, path):
        """Set board config file path (e.g., '/boards/esp32s3.json')"""
        # Extract filename from path
        if '/' in path:
            filename = path.split('/')[-1]
        else:
            filename = path
        
        # Ensure it has .json extension
        if not filename.endswith('.json'):
            filename = f'{filename}.json'
        
        self.data['board'] = filename
        # Remove old board_config if it exists
        if 'board_config' in self.data:
            del self.data['board_config']
    
    # Timezone methods
    def get_timezone_offset_seconds(self):
        """Get timezone offset in seconds from UTC."""
        return self.data.get('timezone', {}).get('offset_seconds', 0)
    
    def get_timezone_name(self):
        """Get timezone name (e.g., 'America/Los_Angeles')."""
        return self.data.get('timezone', {}).get('name', 'UTC')
    
    def set_timezone(self, name, offset_seconds):
        """Set timezone configuration.
        
        Args:
            name: Timezone name (e.g., 'America/Los_Angeles')
            offset_seconds: Offset from UTC in seconds
        """
        self.data['timezone'] = {
            "name": name,
            "offset_seconds": offset_seconds
        }
    
    # Time methods
    def get_last_known_time(self):
        """Get last known time (unix timestamp).
        
        Returns:
            Unix timestamp or None if never set
        """
        return self.data.get('last_known_time')
    
    def set_last_known_time(self, timestamp):
        """Save last known time (unix timestamp)."""
        self.data['last_known_time'] = timestamp
    
    # Sensor pin methods
    def _get_sensor_pins_defaults(self):
        """Get default sensor pin configuration."""
        return {
            "i2c_scl": -1,
            "i2c_sda": -1,
            "ds18b20": -1,
            "photo_sensor": -1,
            "light_switch": -1,
            "reset_switch": -1
        }
    
    def get_sensor_pins(self):
        """Get sensor pin configuration with defaults for missing keys."""
        defaults = self._get_sensor_pins_defaults()
        saved = self.data.get('sensor_pins', {})
        # Merge saved values over defaults
        return {**defaults, **saved}
    
    def get_sensor_pin(self, key):
        """Get a specific sensor pin value.
        
        Args:
            key: One of 'i2c_scl', 'i2c_sda', 'ds18b20', 'photo_sensor', 
                 'light_switch', 'reset_switch'
        
        Returns:
            Pin number or -1 if disabled
        """
        pins = self.get_sensor_pins()
        return pins.get(key, -1)
    
    def set_sensor_pins(self, pins_dict):
        """Set sensor pin configuration.
        
        Args:
            pins_dict: Dictionary with sensor pin assignments
                       e.g., {"i2c_scl": 1, "i2c_sda": 2, "ds18b20": 38}
        
        Returns:
            True if valid, False otherwise
        """
        valid_keys = set(self._get_sensor_pins_defaults().keys())
        
        # Validate keys
        for key in pins_dict.keys():
            if key not in valid_keys:
                print(f"Warning: Unknown sensor pin key: {key}")
                return False
        
        # Validate values (must be integers)
        for key, value in pins_dict.items():
            if not isinstance(value, int):
                print(f"Warning: Sensor pin value must be integer: {key}={value}")
                return False
        
        # Merge with existing config
        if 'sensor_pins' not in self.data:
            self.data['sensor_pins'] = {}
        
        self.data['sensor_pins'].update(pins_dict)
        return True
    
    def get_all(self):
        """Get all configuration as dict."""
        return self.data.copy()

