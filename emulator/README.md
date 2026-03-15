# ESP32 MicroPython Emulator

Run the application locally on CPython without real hardware. MicroPython modules (`machine`, `network`, `esp32`, etc.) are stubbed out, and sensor values are driven by an editable JSON file.

## Quick Start

```bash
python3 emulator/run.py
```

This will:
1. Create `emulator/fs/` with default config files and symlinks to `boards/` on first run
2. Boot the full application (instances, sensors, relays, web server, automation loop)
3. Start the web server on `http://localhost:8080`

Use `--port` to change the port:
```bash
python3 emulator/run.py --port 3000
```

## Simulating Sensor Values

Edit `emulator/sim_config.json` while the emulator is running:

```json
{
    "temperature": 25.0,
    "humidity": 50.0,
    "light_level": 2000,
    "switch_state": false,
    "reset_switch_state": false
}
```

Changes are picked up within ~5 seconds. The automation loop will evaluate rules against the new values and toggle relays accordingly. GPIO state changes are printed to the console:

```
Rule for 'MyRelay': get_temperature() > 30 -> True
[GPIO] Pin 10 -> HIGH
```

## What Works

- Full automation loop (sensor read -> rule evaluation -> relay toggle)
- Web server + all REST API endpoints on localhost
- Config management (config.json, relays.json, board configs)
- Rule engine with live sensor context
- NeoPixel LED state changes logged to console

## What Doesn't (by design)

- Real WiFi (stub always reports connected at 127.0.0.1)
- Real NTP sync (uses system clock)
- Real sensor hardware (uses sim_config.json)
- WebREPL / mDNS (no-op stubs)

## Files

| File | Purpose |
|------|---------|
| `run.py` | Entry point — sets up stubs, boots the app |
| `stubs.py` | All MicroPython module stubs and CPython patches |
| `sim_config.json` | Simulated sensor values (edit while running) |
| `fs/` | Virtual filesystem (generated on first run, gitignored) |
