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
        
        # Initialize config manager
        self.config = ConfigManager()
        print(f"✓ ConfigManager initialized")
        
        # Initialize board config
        self.board = BoardConfig(self.config.get_board_config_file())
        print(f"✓ BoardConfig initialized: {self.board.get_name()}")
        
        # Set CPU clock speed from board config
        self.board.set_cpu_frequency()
        
        # Initialize WiFi manager
        self.wifi = WiFiManager(self.config)
        print(f"✓ WiFiManager initialized")
        
        # Initialize relay manager
        self.relays = RelayManager()
        print(f"✓ RelayManager initialized ({len(self.relays.get_relays().get('relays', []))} relays)")
        
        # Initialize sensor manager
        self.sensors = SensorManager()
        print(f"✓ SensorManager initialized")
        
        # Initialize time sync
        self.time_sync = TimeSync()
        print(f"✓ TimeSync initialized")
        
        # Initialize rule engine (needs sensors and time_sync)
        self.rules = RuleEngine(self.sensors, self.time_sync)
        print(f"✓ RuleEngine initialized")
        
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
        lines.append(f"  rules:     {type(self.rules).__name__ if self.rules else 'Not initialized'}")
        lines.append(f"  server:    {type(self.server).__name__ if self.server else 'Not initialized'}")
        return "\n".join(lines)

# Global singleton instance manager
instances = InstanceManager()

