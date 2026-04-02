# MicroPython ESP32 Framework

## Quick Reference

- **Provision a new board**: `./scripts/provision.sh <port> <config_dir>`
- **Deploy code changes**: `./scripts/deploy_src.sh`
- **Deploy web UI changes**: `./scripts/deploy_web.sh`
- **Monitor serial output**: `./scripts/monitor.sh`
- **Per-device configs**: `device_configs/<name>/config.json` (and optionally `relays.json`)

## Provisioning Gotchas

### Boot ordering matters
`boot.py` and `main.py` must be uploaded LAST. Once they're on the board, the
full app starts on every reboot, which blocks serial tools (ampy/mpremote) from
entering raw REPL for subsequent uploads. The `provision.sh` and `deploy_src.sh`
scripts handle this automatically.

### ampy vs mpremote
`mpremote` has been unreliable at entering raw REPL on some boards (especially
NodeMCU-32S with CH340 USB-serial chips). `ampy` (`adafruit-ampy`) works more
reliably for initial provisioning. Both are installable via `pipx`.

If both tools fail on a board that's already running the app, use pyserial
directly to interrupt (Ctrl-C), enter raw REPL (Ctrl-A), and execute commands.

### Flash baud rate
Use 115200 for flashing firmware. 460800 can be flaky on some USB-serial chips
and cause "chip stopped responding" errors mid-write. The provision script
defaults to 115200.

### Case-sensitive filesystem
MicroPython's filesystem (LittleFS on ESP32) is case-sensitive. The AHT21 sensor
driver file is `aht21.py` (lowercase) to match the `from aht21 import AHT21`
import in `sensors.py`.

### ESP32 only supports 2.4GHz WiFi
If WiFi connection times out, verify the SSID is for a 2.4GHz network.

## Project Structure

```
src/              # MicroPython source (deployed to board root)
boards/           # Board pin definitions (deployed to /boards/ on device)
preact/           # Web UI (Preact app, built and deployed to /www/ as gzip)
scripts/          # Host-side shell scripts
firmware/         # Downloaded .bin files (gitignored)
device_configs/   # Per-device config.json/relays.json (gitignored, contains WiFi passwords)
tests/            # Unit tests
emulator/         # Desktop emulator
```

## Supported Boards

Board configs are in `boards/*.json`. Currently:
- `nodemcu_32s.json` - Original ESP32 (NodeMCU-32S)
- `esp32s3_devkitc_1_n16r8v.json` - ESP32-S3 DevKitC
- `esp32s3_antenna_n16r8v.json` - ESP32-S3 with external antenna
- `esp32c6_devkit.json` - ESP32-C6 DevKit

## Sensor & Relay Configuration

Sensors and relays are configured via JSON files on the device, not in code:
- `config.json` - WiFi, hostname, board selection, sensor pin assignments
- `relays.json` - Relay pins, labels, and automation rules

See `device_configs/README.md` for the full schema.

## Rule Engine

Relay automation rules are Python expressions evaluated in a sandboxed environment.
Available functions:
- `get_temperature()`, `get_humidity()`, `get_light_level()`, `get_switch_state()`
- `get_last_temperature()`, etc. (previous reading, for edge detection)
- `get_time()` - seconds since midnight (local time if timezone detected)
- `time(hour, minute, second)` - helper to create time values

Rules return `True` (relay on), `False` (relay off), or `None` (keep current state,
useful for hysteresis).

Multi-line rules use a `result` variable:
```python
temp = get_temperature()
result = None if temp is None else (True if temp < 18 else (False if temp > 28 else None))
```
