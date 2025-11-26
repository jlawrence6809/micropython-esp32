# boot.py - Runs on every boot
from instances import instances

# Initialize all singleton instances
instances.initialize()

def setup_wifi():
    """Setup WiFi with AP fallback."""
    
    # WiFi manager handles everything: hostname, credentials, connection, mDNS
    mode, mdns_server = instances.wifi.setup_and_connect()
    
    if mode == 'sta':
        print('WiFi connected successfully!')
        
        # Sync time with NTP server
        print("=" * 50)
        instances.time_sync.sync()
        print("=" * 50)
        
        # Start WebREPL if in station mode
        try:
            import webrepl
            webrepl.start()
            print('WebREPL started')
        except Exception as e:
            print(f'WebREPL failed to start: {e}')
    else:
        hostname = instances.config.get_hostname()
        print(f'Running in AP mode - connect to "{hostname}-setup" to configure WiFi')
        print(f'AP IP: {instances.wifi.get_ip()}')
    
    return mdns_server

# Setup WiFi on boot
mdns_server = setup_wifi()
