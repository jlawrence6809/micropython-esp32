# boot.py - Runs on every boot
# This file initializes all singleton instances and connects to WiFi

import network
import time

# Import instance manager and all component classes
from instances import instances
from config_manager import ConfigManager
from board_config import BoardConfig
from wifi_manager import WiFiManager
from relays import RelayManager
from sensors import SensorManager
from rule_engine import RuleEngine

print("=" * 50)
print("Initializing system singletons...")
print("=" * 50)

# Initialize all singleton instances via the instance manager
instances.config = ConfigManager()
print(f"✓ ConfigManager initialized")

instances.board = BoardConfig(instances.config.get_board_config_file())
print(f"✓ BoardConfig initialized: {instances.board.get_name()}")

instances.wifi = WiFiManager(instances.config)
print(f"✓ WiFiManager initialized")

instances.relays = RelayManager()
print(f"✓ RelayManager initialized ({len(instances.relays.get_relays().get('relays', []))} relays)")

instances.sensors = SensorManager()
print(f"✓ SensorManager initialized")

instances.rules = RuleEngine(instances.sensors)
print(f"✓ RuleEngine initialized")

print("=" * 50)

def setup_mdns(hostname):
    """Setup mDNS responder for hostname.local access."""
    try:
        import mdns
        mdns_server = mdns.Server()
        mdns_server.start(hostname, "MicroPython ESP32 Automation")
        print(f"mDNS started: {hostname}.local")
        return mdns_server
    except ImportError:
        print("mDNS not available (requires esp32 port with mdns module)")
        return None
    except Exception as e:
        print(f"Failed to start mDNS: {e}")
        return None

def setup_wifi():
    """Setup WiFi with AP fallback."""
    hostname = instances.config.get_hostname()
    
    # Check if WiFi credentials are configured
    if not instances.config.get_wifi_ssid() or not instances.config.get_wifi_password():
        print('WiFi credentials not configured, starting AP mode...')
        instances.wifi.start_ap_mode()
        print(f"Connect to '{hostname}-setup' network to configure WiFi")
        return None
    
    # Set hostname before connecting
    try:
        network.hostname(hostname)
        print(f'Hostname set to: {hostname}')
    except Exception as e:
        print(f'Failed to set hostname: {e}')
    
    # Try to connect with AP fallback
    mode = instances.wifi.connect_with_fallback()
    
    mdns_server = None
    if mode == 'sta':
        print('WiFi connected successfully!')
        
        # Start mDNS for hostname.local access
        mdns_server = setup_mdns(hostname)
        
        # Start WebREPL if in station mode
        try:
            import webrepl
            webrepl.start()
            print('WebREPL started')
        except Exception as e:
            print(f'WebREPL failed to start: {e}')
    else:
        print(f'Running in AP mode - connect to "{hostname}-setup" to configure WiFi')
        print(f'AP IP: {instances.wifi.get_ip()}')
    
    return mdns_server

# Setup WiFi on boot
mdns_server = setup_wifi()

print("=" * 50)
print("Boot complete! Access singletons via 'instances':")
print("  from instances import instances")
print("  instances.config   - ConfigManager")
print("  instances.board    - BoardConfig")
print("  instances.wifi     - WiFiManager")
print("  instances.relays   - RelayManager")
print("  instances.sensors  - SensorManager")
print("  instances.rules    - RuleEngine")
print("=" * 50)
