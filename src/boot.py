# boot.py - Runs on every boot
import network
import time
from instances import instances

# Initialize all singleton instances
instances.initialize()

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
        
        # Sync time with NTP server
        print("=" * 50)
        instances.time_sync.sync()
        print("=" * 50)
        
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
