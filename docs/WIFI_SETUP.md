# WiFi and WebREPL Setup Guide

## Step 1: Connect to WiFi

### Option A: Quick Test in REPL

Connect via `./monitor.sh` and run:

```python
>>> import network
>>> wlan = network.WLAN(network.STA_IF)
>>> wlan.active(True)
>>> wlan.connect('YOUR_WIFI_NAME', 'YOUR_PASSWORD')

# Wait a few seconds, then check:
>>> wlan.isconnected()
True
>>> wlan.ifconfig()
('192.168.1.xxx', '255.255.255.0', '192.168.1.1', '8.8.8.8')
```

### Option B: Upload WiFi Test Script

```bash
./upload.sh wifi_test.py
```

Then in the REPL:

```python
>>> import wifi_test
>>> wifi_test.scan_networks()  # See available networks
>>> wifi_test.connect_wifi('YOUR_SSID', 'YOUR_PASSWORD')
```

### Option C: Auto-Connect on Boot

1. Edit `boot.py` and add your WiFi credentials
2. Uncomment the `connect_wifi()` line at the bottom
3. Upload it:
   ```bash
   ./upload.sh boot.py
   ```
4. Reset the board - it will auto-connect on every boot!

## Step 2: Set Up WebREPL

WebREPL lets you access the REPL wirelessly via a web browser!

### Initial Setup (One-Time)

1. Make sure you're connected to WiFi (see Step 1)

2. In the REPL, run:

   ```python
   >>> import webrepl_setup
   ```

3. Follow the prompts:
   - Enable WebREPL on boot? **E** (yes)
   - Set a password (remember this!)
   - Reboot when prompted

OR upload the helper script:

```bash
./upload.sh setup_webrepl.py
```

Then in REPL:

```python
>>> import setup_webrepl
```

### Using WebREPL

1. Make sure your board is connected to WiFi and WebREPL is enabled

2. Get your board's IP address:

   ```python
   >>> import network
   >>> wlan = network.WLAN(network.STA_IF)
   >>> wlan.ifconfig()[0]
   '192.168.1.xxx'
   ```

3. Open the WebREPL client in your browser:

   - Online: http://micropython.org/webrepl/
   - Or download it locally from: https://github.com/micropython/webrepl

4. Connect to: `ws://192.168.1.xxx:8266` (use your board's IP)

5. Enter the password you set

6. You now have wireless REPL access! You can:
   - Type Python commands
   - Upload files via the "Send a file" button
   - Download files from the board

## Troubleshooting

### WiFi won't connect

- Check SSID and password are correct
- Make sure your WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Try scanning: `wlan.scan()` to see if your network is visible

### WebREPL not accessible

- Check WiFi is connected: `wlan.isconnected()`
- Verify WebREPL is enabled: `import webrepl; webrepl.start()`
- Check firewall settings on your computer
- Make sure you're on the same network as the ESP32

### Reset WebREPL password

Delete `webrepl_cfg.py` from the board and run `webrepl_setup` again:

```python
>>> import os
>>> os.remove('webrepl_cfg.py')
>>> import webrepl_setup
```

## Tips

- **Save your WiFi credentials**: Put them in `boot.py` for auto-connect
- **WebREPL is slower than USB**: Use USB for development, WebREPL for convenience
- **Security**: WebREPL password protects access, but it's not encrypted
- **Access Point mode**: ESP32 can also create its own WiFi network if needed
