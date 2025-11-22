# boot.py - Runs on every boot
# This file connects to WiFi automatically when the board starts

import network
import time

# Import WiFi credentials from config.py
try:
    from config import WIFI_SSID, WIFI_PASSWORD
    try:
        from config import HOSTNAME
    except ImportError:
        HOSTNAME = None
except ImportError:
    print('Warning: config.py not found. WiFi disabled.')
    print('Create config.py with WIFI_SSID and WIFI_PASSWORD')
    WIFI_SSID = None
    WIFI_PASSWORD = None
    HOSTNAME = None

def connect_wifi():
    """Connect to WiFi network"""
    if not WIFI_SSID or not WIFI_PASSWORD:
        print('WiFi credentials not configured')
        return
    
    wlan = network.WLAN(network.STA_IF)
    
    # Set hostname before activating (must be done before active(True))
    if HOSTNAME:
        try:
            network.hostname(HOSTNAME)
            print(f'Hostname set to: {HOSTNAME}.local')
        except Exception as e:
            print(f'Failed to set hostname: {e}')
    
    wlan.active(True)
    
    if wlan.isconnected():
        print('Already connected to WiFi')
        print('Network config:', wlan.ifconfig())
        return
    
    print(f'Connecting to WiFi: {WIFI_SSID}...')
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Wait for connection (max 10 seconds)
    max_wait = 10
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print('Waiting for connection...')
        time.sleep(1)
    
    if wlan.isconnected():
        print('Connected to WiFi!')
        print('Network config:', wlan.ifconfig())
        print('IP address:', wlan.ifconfig()[0])
    else:
        print('Failed to connect to WiFi')

# Auto-connect to WiFi on boot
connect_wifi()

# Start WebREPL if WiFi is connected
if WIFI_SSID and WIFI_PASSWORD:
    try:
        import webrepl
        webrepl.start()
        print('WebREPL started')
    except Exception as e:
        print(f'WebREPL failed to start: {e}')

