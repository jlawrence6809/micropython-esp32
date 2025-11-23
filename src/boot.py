# boot.py - Runs on every boot
# This file connects to WiFi with AP fallback and sets up mDNS

import network
import time
from wifi_manager import WiFiManager
from config_manager import config

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
    hostname = config.HOSTNAME if config.HOSTNAME else "esp32"
    
    # Check if WiFi credentials are configured
    if not config.WIFI_SSID or not config.WIFI_PASSWORD:
        print('WiFi credentials not configured, starting AP mode...')
        wifi = WiFiManager()
        wifi.start_ap_mode()
        print(f"Connect to '{hostname}-setup' network to configure WiFi")
        return wifi, None
    
    # Set hostname before connecting
    try:
        network.hostname(hostname)
        print(f'Hostname set to: {hostname}')
    except Exception as e:
        print(f'Failed to set hostname: {e}')
    
    # Try to connect with AP fallback
    wifi = WiFiManager()
    mode = wifi.connect_with_fallback()
    
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
        print(f'AP IP: {wifi.get_ip()}')
    
    return wifi, mdns_server

# Setup WiFi on boot
wifi_manager, mdns_server = setup_wifi()
