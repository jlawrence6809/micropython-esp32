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
            "board": "unconfigured.json"
        }
    
    def save(self):
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
    
    # Board property (filename-based)
    @property
    def BOARD(self):
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
                self.save()
        
        board = self.data.get('board', 'unconfigured.json')
        # Ensure it has .json extension
        if not board.endswith('.json'):
            board = f'{board}.json'
        return board
    
    @BOARD.setter
    def BOARD(self, value):
        """Set board filename"""
        # Ensure it has .json extension
        if not value.endswith('.json'):
            value = f'{value}.json'
        self.data['board'] = value
        # Remove old board_config if it exists
        if 'board_config' in self.data:
            del self.data['board_config']
    
    @property
    def BOARD_CONFIG_FILE(self):
        """Get full board config file path"""
        return f'/boards/{self.BOARD}'
    
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

