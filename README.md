# MicroPython ESP32 IoT Framework

A general-purpose MicroPython automation platform for ESP32 microcontrollers. Provides JSON-based configuration, a rule engine for relay automation, sensor management, and a Preact web UI -- all configurable without code changes.

## Supported Boards

- **NodeMCU-32S** - Original ESP32 (`nodemcu_32s.json`)
- **ESP32-S3-DevKitC-1-N16R8V** - ESP32-S3 with 16MB flash / 8MB PSRAM (`esp32s3_devkitc_1_n16r8v.json`)
- **ESP32-S3 External Antenna** - ESP32-S3 variant (`esp32s3_antenna_n16r8v.json`)
- **ESP32-C6 DevKit** - ESP32-C6 (`esp32c6_devkit.json`)

## Quick Start

### 1. Install Dependencies

```bash
pipx install esptool
pipx install adafruit-ampy
```

### 2. Download Firmware

```bash
./scripts/download_firmware.sh
```

Edit the script to uncomment the firmware URL for your chip variant (ESP32 vs ESP32-S3).

### 3. Create a Device Config

```bash
mkdir -p device_configs/myboard
cat > device_configs/myboard/config.json << 'EOF'
{
  "wifi": { "ssid": "MyNetwork", "password": "MyPassword" },
  "hostname": "myboard",
  "board": "nodemcu_32s.json"
}
EOF
```

See `device_configs/README.md` for full config schema including sensor pins and relay rules.

### 4. Provision the Board

Connect the board via USB, then:

```bash
./scripts/provision.sh /dev/tty.usbserial-0001 myboard
```

This will erase flash, write MicroPython firmware, upload all source code, board configs, device config, and the web UI in one step.

If the board won't connect during flash, hold the **BOOT** button while the script connects.

### 5. Access the Web UI

After provisioning, the board connects to WiFi and prints its IP to serial. Open it in a browser to see relay controls, sensor readings, and system info.

If no WiFi is configured, the board starts an AP named `<hostname>-setup` (password: `12345678`). Connect to it and configure WiFi at `http://192.168.4.1`.

## Updating Code

After the initial provision, use the deploy scripts for incremental updates:

```bash
./scripts/deploy_src.sh     # Upload Python source files
./scripts/deploy_web.sh     # Build and upload the Preact web UI
```

## Understanding MicroPython Execution

**Important:** MicroPython is single-threaded. It can either run your code (`main.py`) OR provide an interactive prompt (REPL), but not both at the same time.

- **Running mode**: On boot, `boot.py` initializes the system, then `main.py` starts the web server and automation loop.
- **REPL mode**: Connecting via serial and pressing Enter/Ctrl-C interrupts the running code and drops into a `>>>` prompt. This kills the web server.
- **Restart**: From REPL, press Ctrl-D for a soft reboot, or run `import machine; machine.reset()` for a hard reboot.

### Viewing Logs Without Stopping the Server

1. Connect via `./scripts/monitor.sh`
2. Press the **RESET** button on the board
3. Watch the boot logs scroll by
4. **Do not press any keys** or you will interrupt the server

## WebREPL

WebREPL doesn't work over HTTPS. Open in an incognito window:

```
http://micropython.org/webrepl/#<board-ip>:8266
```

## Resources

- [MicroPython Documentation](https://docs.micropython.org/)
- [ESP32 Quick Reference](https://docs.micropython.org/en/latest/esp32/quickref.html)
