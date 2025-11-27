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
    
    def get_all(self):
        """Get all configuration as dict."""
        return self.data.copy()

