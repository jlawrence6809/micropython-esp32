# wifi_test.py - Test WiFi connection
# Run this in the REPL or upload it to test WiFi

import network
import time

def scan_networks():
    """Scan for available WiFi networks"""
    print("Scanning for WiFi networks...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    
    print(f"\nFound {len(networks)} networks:")
    for ssid, bssid, channel, RSSI, authmode, hidden in networks:
        print(f"  {ssid.decode('utf-8'):32} | Channel: {channel:2} | RSSI: {RSSI} dBm")

def connect_wifi(ssid, password):
    """Connect to a WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print('Already connected')
        print('IP address:', wlan.ifconfig()[0])
        return True
    
    print(f'\nConnecting to {ssid}...')
    wlan.connect(ssid, password)
    
    max_wait = 10
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        time.sleep(1)
    
    if wlan.isconnected():
        print('✓ Connected!')
        config = wlan.ifconfig()
        print(f'  IP address:  {config[0]}')
        print(f'  Subnet mask: {config[1]}')
        print(f'  Gateway:     {config[2]}')
        print(f'  DNS server:  {config[3]}')
        return True
    else:
        print('✗ Failed to connect')
        return False

def disconnect_wifi():
    """Disconnect from WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)
    print('Disconnected from WiFi')

if __name__ == '__main__':
    # Example usage
    scan_networks()
    
    # Uncomment and fill in your credentials to test connection
    # connect_wifi('YOUR_SSID', 'YOUR_PASSWORD')

