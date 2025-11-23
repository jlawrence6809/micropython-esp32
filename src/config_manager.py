import json

class Config:
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
            "board_config": "/boards/esp32s3_devkitc_1_n16r8v.json"
        }
    
    def save(self):
        """Save configuration to JSON file."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
            print(f"Configuration saved to {self.CONFIG_FILE}")
            return True
        except OSError as e:
            print(f"Failed to save configuration: {e}")
            return False
    
    # WiFi properties
    @property
    def WIFI_SSID(self):
        return self.data.get('wifi', {}).get('ssid')
    
    @WIFI_SSID.setter
    def WIFI_SSID(self, value):
        if 'wifi' not in self.data:
            self.data['wifi'] = {}
        self.data['wifi']['ssid'] = value
    
    @property
    def WIFI_PASSWORD(self):
        return self.data.get('wifi', {}).get('password')
    
    @WIFI_PASSWORD.setter
    def WIFI_PASSWORD(self, value):
        if 'wifi' not in self.data:
            self.data['wifi'] = {}
        self.data['wifi']['password'] = value
    
    # Hostname property
    @property
    def HOSTNAME(self):
        return self.data.get('hostname', 'esp32')
    
    @HOSTNAME.setter
    def HOSTNAME(self, value):
        self.data['hostname'] = value
    
    # Board config property
    @property
    def BOARD_CONFIG_FILE(self):
        return self.data.get('board_config', '/boards/esp32s3_devkitc_1_n16r8v.json')
    
    @BOARD_CONFIG_FILE.setter
    def BOARD_CONFIG_FILE(self, value):
        self.data['board_config'] = value
    
    def update_wifi(self, ssid, password):
        """Update WiFi credentials and save."""
        self.WIFI_SSID = ssid
        self.WIFI_PASSWORD = password
        return self.save()
    
    def get_all(self):
        """Get all configuration as dict."""
        return self.data.copy()

# Global config instance
config = Config()

