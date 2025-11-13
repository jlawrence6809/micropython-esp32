# check_webrepl.py - Check WiFi and WebREPL status
# Run this to troubleshoot WebREPL connection issues

import network

print("=" * 50)
print("WiFi and WebREPL Status Check")
print("=" * 50)
print()

# Check WiFi connection
wlan = network.WLAN(network.STA_IF)
print(f"WiFi Interface Active: {wlan.active()}")
print(f"WiFi Connected: {wlan.isconnected()}")

if wlan.isconnected():
    config = wlan.ifconfig()
    print(f"IP Address: {config[0]}")
    print(f"Subnet Mask: {config[1]}")
    print(f"Gateway: {config[2]}")
    print(f"DNS: {config[3]}")
    print()
    print(f"WebREPL URL: ws://{config[0]}:8266")
    
    # Check hostname
    try:
        hostname = network.hostname()
        print(f"Hostname: {hostname}")
        print(f"mDNS URL: ws://{hostname}.local:8266")
    except:
        print("Hostname: Not set")
else:
    print("\n⚠️  Not connected to WiFi!")
    print("Run boot.connect_wifi() to connect")

print()

# Check if WebREPL module exists
try:
    import webrepl
    print("✓ webrepl module found")
    
    # Try to start WebREPL
    try:
        webrepl.start()
        print("✓ WebREPL started on port 8266")
    except Exception as e:
        print(f"WebREPL start result: {e}")
        
except ImportError:
    print("✗ webrepl module not found in firmware")

print()

# Check for WebREPL config file
try:
    import os
    files = os.listdir()
    if 'webrepl_cfg.py' in files:
        print("✓ webrepl_cfg.py exists (WebREPL is configured)")
        try:
            import webrepl_cfg
            print(f"  Password is set: {bool(webrepl_cfg.PASS)}")
        except:
            pass
    else:
        print("✗ webrepl_cfg.py not found")
        print("  Run: import webrepl_setup")
except Exception as e:
    print(f"Could not check files: {e}")

print()
print("=" * 50)

