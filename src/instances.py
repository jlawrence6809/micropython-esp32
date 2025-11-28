# instances.py - Global singleton instance manager
# This module provides a centralized location for all singleton instances

class InstanceManager:
    """Manages all singleton instances for the application.
    
    This provides a clean namespace for accessing all system components
    from anywhere in the code or from the REPL.
    
    Usage:
        from instances import instances
        
        # Access any singleton
        instances.relays.get_relays()
        instances.sensors.get_temperature()
        instances.config.get_hostname()
    """
    
    def __init__(self):
        # Core configuration and board
        self.config = None          # ConfigManager instance
        self.board = None           # BoardConfig instance
        
        # Network and connectivity
        self.wifi = None            # WiFiManager instance
        self.time_sync = None       # TimeSync instance
        
        # Hardware control
        self.relays = None          # RelayManager instance
        self.sensors = None         # SensorManager instance
        self.led = None             # BoardRgbLed instance
        
        # Automation
        self.rules = None           # RuleEngine instance
        
        # Server (set later in main.py)
        self.server = None          # WebServer instance
    
    def initialize(self):
        """Initialize all singleton instances.
        
        This is called from boot.py to set up all system components.
        """
        print("=" * 50)
        print("Initializing system singletons...")
        print("=" * 50)
        
        # Import here to avoid circular dependencies
        from config_manager import ConfigManager
        from board_config import BoardConfig
        from wifi_manager import WiFiManager
        from relays import RelayManager
        from sensors import SensorManager
        from rule_engine import RuleEngine
        from time_sync import TimeSync
        from web_server import WebServer
        from board_rgb_led import BoardRgbLed
        
        # Initialize config manager
        self.config = ConfigManager()
        print(f"✓ ConfigManager initialized")
        
        # Initialize board config (gets board file from config)
        # Must be initialized after ConfigManager
        self.board = BoardConfig()
        print(f"✓ BoardConfig initialized: {self.board.get_name()}")
        
        # Initialize WiFi manager (uses config from instances)
        self.wifi = WiFiManager()
        print(f"✓ WiFiManager initialized")
        
        # Initialize relay manager
        self.relays = RelayManager()
        print(f"✓ RelayManager initialized ({len(self.relays.get_relays().get('relays', []))} relays)")
        
        # Initialize sensor manager
        self.sensors = SensorManager()
        print(f"✓ SensorManager initialized")
        
        # Initialize RGB LED
        self.led = BoardRgbLed()
        # LED starts in 'off' state, will be set to 'booting' in boot.py
        
        # Initialize time sync
        self.time_sync = TimeSync()
        print(f"✓ TimeSync initialized")
        
        # Initialize rule engine (uses sensors and time_sync from instances)
        self.rules = RuleEngine()
        print(f"✓ RuleEngine initialized")
        
        # Initialize web server
        self.server = WebServer()
        print(f"✓ WebServer initialized")
        
        print("=" * 50)
    
    def __repr__(self):
        """Pretty print available instances."""
        lines = ["Available Instances:"]
        lines.append(f"  config:    {type(self.config).__name__ if self.config else 'Not initialized'}")
        lines.append(f"  board:     {type(self.board).__name__ if self.board else 'Not initialized'}")
        lines.append(f"  wifi:      {type(self.wifi).__name__ if self.wifi else 'Not initialized'}")
        lines.append(f"  time_sync: {type(self.time_sync).__name__ if self.time_sync else 'Not initialized'}")
        lines.append(f"  relays:    {type(self.relays).__name__ if self.relays else 'Not initialized'}")
        lines.append(f"  sensors:   {type(self.sensors).__name__ if self.sensors else 'Not initialized'}")
        lines.append(f"  led:       {type(self.led).__name__ if self.led else 'Not initialized'}")
        lines.append(f"  rules:     {type(self.rules).__name__ if self.rules else 'Not initialized'}")
        lines.append(f"  server:    {type(self.server).__name__ if self.server else 'Not initialized'}")
        return "\n".join(lines)

# Global singleton instance manager
instances = InstanceManager()

