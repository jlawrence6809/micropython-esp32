# Configuration Migration Guide

## Migrating from config.py to config.json

The project now uses JSON-based configuration instead of Python files for easier programmatic updates.

### Old Format (`config.py`)

```python
WIFI_SSID = "MyNetwork"
WIFI_PASSWORD = "mypassword"
HOSTNAME = "esp32"
BOARD_CONFIG_FILE = "/boards/esp32s3_devkitc_1_n16r8v.json"
```

### New Format (`config.json`)

```json
{
  "wifi": {
    "ssid": "MyNetwork",
    "password": "mypassword"
  },
  "hostname": "esp32",
  "board_config": "/boards/esp32s3_devkitc_1_n16r8v.json"
}
```

### Migration Steps

1. **Copy your existing config.py values**
2. **Create config.json** from `config.example.json`:
   ```bash
   cp config.example.json config.json
   ```
3. **Edit config.json** with your values
4. **Deploy**:
   ```bash
   ./scripts/deploy_src.sh
   ```

### Benefits of JSON Config

✅ **Programmatic Updates** - WiFi credentials can be saved from the web interface  
✅ **No String Parsing** - Clean JSON read/write  
✅ **Validation** - JSON schema validation possible  
✅ **Standard Format** - Works with any JSON tool

### Backward Compatibility

The old `config.py` is now excluded from deployment. The system will use default values if `config.json` is not found.

### mDNS Support

With the new config system, mDNS is automatically enabled. Access your device at:

```
http://{hostname}.local
```

For example, if `hostname` is "esp32":

```
http://esp32.local
```

### AP Mode SSID

The AP mode SSID now uses your hostname:

- Old: `ESP32-Setup`
- New: `{hostname}-setup` (e.g., `esp32-setup`)

This makes it easier to identify your device when multiple ESP32s are in setup mode.
