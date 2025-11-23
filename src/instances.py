# instances.py - Global singleton instance manager
# This module provides a centralized location for all singleton instances

class InstanceManager:
    """Manages all singleton instances for the application.
    
    This provides a clean namespace for accessing all system components
    from anywhere in the code or from the REPL.
    
    Usage:
        from instances import instances
        
        # Access any singleton
        instances.relay_manager.get_relays()
        instances.sensor_manager.get_temperature()
        instances.config.get_hostname()
    """
    
    def __init__(self):
        # Core configuration and board
        self.config = None          # ConfigManager instance
        self.board = None           # BoardConfig instance
        
        # Network and connectivity
        self.wifi = None            # WiFiManager instance
        
        # Hardware control
        self.relays = None          # RelayManager instance
        self.sensors = None         # SensorManager instance
        
        # Automation
        self.rules = None           # RuleEngine instance
        
        # Server (set later in main.py)
        self.server = None          # WebServer instance
    
    def __repr__(self):
        """Pretty print available instances."""
        lines = ["Available Instances:"]
        lines.append(f"  config:  {type(self.config).__name__ if self.config else 'Not initialized'}")
        lines.append(f"  board:   {type(self.board).__name__ if self.board else 'Not initialized'}")
        lines.append(f"  wifi:    {type(self.wifi).__name__ if self.wifi else 'Not initialized'}")
        lines.append(f"  relays:  {type(self.relays).__name__ if self.relays else 'Not initialized'}")
        lines.append(f"  sensors: {type(self.sensors).__name__ if self.sensors else 'Not initialized'}")
        lines.append(f"  rules:   {type(self.rules).__name__ if self.rules else 'Not initialized'}")
        lines.append(f"  server:  {type(self.server).__name__ if self.server else 'Not initialized'}")
        return "\n".join(lines)

# Global singleton instance manager
instances = InstanceManager()

