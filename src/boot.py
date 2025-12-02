# boot.py - Runs on every boot
from instances import instances

# Initialize all singleton instances
instances.initialize()

# Set CPU clock speed from board config
instances.board.set_cpu_frequency()

# Set LED to booting state
instances.led.set_state('booting')

def setup_wifi():
    """Setup WiFi with AP fallback."""
    
    # WiFi manager handles everything: hostname, credentials, connection, mDNS
    mode, mdns_server = instances.wifi.setup_and_connect()
    
    if mode == 'sta':
        print('WiFi connected successfully!')
        
        # Set LED to connected state
        
        # Sync time with NTP server
        print("=" * 50)
        sync_success = instances.time_sync.sync()
        
        # If sync failed, try to restore from config
        if not sync_success:
            print("Attempting to restore time from last known value...")
            instances.time_sync.restore_from_config()
        
        print("=" * 50)
        
        # Detect timezone with exponential backoff retries
        print("=" * 50)
        tz_info = instances.time_sync.detect_timezone()
        if tz_info:
            # Save to config
            instances.config.set_timezone(
                tz_info["timezone"],
                tz_info["utc_offset_seconds"]
            )
            instances.config.save_config()
            
            # Apply to time_sync
            instances.time_sync.TIMEZONE_OFFSET = tz_info["utc_offset_seconds"]
        else:
            print("⚠ Timezone detection failed, using saved config")
            # Load from config
            offset = instances.config.get_timezone_offset_seconds()
            instances.time_sync.TIMEZONE_OFFSET = offset
            tz_name = instances.config.get_timezone_name()
            print(f"Timezone: {tz_name} (UTC{offset/3600:+.1f})")
        print("=" * 50)
        
        # Start WebREPL if in station mode
        try:
            import webrepl
            webrepl.start()
            print('WebREPL started')
        except Exception as e:
            print(f'WebREPL failed to start: {e}')
    else:
        # Set LED to AP mode
        instances.led.set_state('ap_mode')
        hostname = instances.config.get_hostname()
        print(f'Running in AP mode - connect to "{hostname}-setup" to configure WiFi')
        print(f'AP IP: {instances.wifi.get_ip()}')
        
        # In AP mode, try to restore time from config
        print("=" * 50)
        print("Attempting to restore time from last known value...")
        instances.time_sync.restore_from_config()
        print("=" * 50)
    
    return mdns_server

# Setup WiFi on boot
mdns_server = setup_wifi()
