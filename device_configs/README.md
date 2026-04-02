# Device Configs

Per-device configuration files. Each subdirectory contains the JSON config files
that get uploaded to a specific board's root filesystem.

## Structure

```
device_configs/
  propagationbox/
    config.json      # WiFi, hostname, board type, sensor pins
    relays.json      # Relay definitions and automation rules
  genericboard/
    config.json
```

## Usage

Reference the directory name when provisioning:

```bash
./scripts/provision.sh /dev/tty.usbserial-0001 propagationbox
```

Or upload manually:

```bash
ampy --port /dev/tty.usbserial-0001 put device_configs/myboard/config.json /config.json
ampy --port /dev/tty.usbserial-0001 put device_configs/myboard/relays.json /relays.json
```

## Config files

### config.json

```json
{
  "wifi": { "ssid": "...", "password": "..." },
  "hostname": "myboard",
  "board": "nodemcu_32s.json",
  "sensor_pins": {
    "i2c_scl": 22,
    "i2c_sda": 21,
    "ds18b20": 19,
    "photo_sensor": -1,
    "light_switch": -1,
    "reset_switch": -1
  }
}
```

- `board` must match a filename in `/boards/`
- Sensor pins default to `-1` (disabled) if omitted
- WiFi can be omitted; the board will start in AP mode for setup

### relays.json

```json
{
  "relays": [
    {
      "pin": 16,
      "label": "Fan",
      "isInverted": false,
      "defaultValue": false,
      "defaultAuto": true,
      "rule": "get_humidity() is not None and get_humidity() > 65"
    }
  ]
}
```

- Omit this file entirely for a board with no relays
- Rules are Python expressions evaluated by the rule engine
- Available functions: `get_temperature()`, `get_humidity()`, `get_light_level()`,
  `get_switch_state()`, `get_time()`, `time(h, m, s)`, plus `get_last_*()` variants
