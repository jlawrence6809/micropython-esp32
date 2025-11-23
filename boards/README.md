# Board Configurations

This directory contains board-specific configuration files for different ESP32 variants. These configurations define GPIO pin availability, reserved pins, and hardware-specific details.

## ⚠️ Important: Configure Your Board

**By default, the system uses `unconfigured.json` which has NO valid GPIO pins.** This is a safety feature to prevent accidentally using wrong pins that could damage your hardware.

**You MUST set your actual board type in `config.json`:**

```json
{
  "board_config": "/boards/esp32s3_devkitc_1_n16r8v.json"
}
```

## Available Boards

### Unconfigured (`unconfigured.json`) - **DEFAULT**

- **Purpose**: Safe default state
- **Valid GPIO**: None (empty list)
- **Use Case**: Prevents accidental GPIO usage before board is configured
- **⚠️ You must configure your actual board to use GPIO pins!**

### ESP32-S3-DevKitC-1-N16R8V (`esp32s3_devkitc_1_n16r8v.json`)

- **Chip**: ESP32-S3
- **Flash**: 16MB
- **PSRAM**: 8MB
- **Valid GPIO**: 1, 2, 4-18, 21, 38-42, 47-48
- **Reserved**: 0, 3, 19-20 (USB), 35-37 (Flash), 43-46 (UART)
- **Reference**: [FluidNC ESP32-S3 Pin Reference](http://wiki.fluidnc.com/en/hardware/ESP32-S3_Pin_Reference)

### ESP32-C6-DevKit (`esp32c6_devkit.json`)

- **Chip**: ESP32-C6
- **Valid GPIO**: 0-11, 18-23
- **Reserved**: 12-17 (SPI Flash)

### NodeMCU-32S (`nodemcu_32s.json`)

- **Chip**: ESP32 (original)
- **Valid GPIO**: 2, 4-5, 12-19, 21-23, 25-27, 32-33
- **Reserved**: 0-1, 3, 6-11 (Flash)
- **Strapping Pins**: 0, 2, 5, 12, 15

## Configuration Format

```json
{
  "name": "Board Name",
  "chip": "ESP32-XX",
  "description": "Board description",
  "clock_speed": 240000000,
  "valid_gpio_pins": [1, 2, 4, ...],
  "reserved_pins": [0, 3, ...],
  "notes": {
    "pin_X": "Special note about pin X"
  },
  "default_sensor_pins": {
    "ds18b20": 38,
    "dht22": 38,
    ...
  },
  "i2c": {
    "scl": 9,
    "sda": 8
  }
}
```

### Field Descriptions

- **`name`**: Human-readable board name (displayed in UI)
- **`chip`**: Chip type (e.g., "ESP32-S3", "ESP32-C6")
- **`description`**: Brief description of the board
- **`clock_speed`**: CPU frequency in Hz (e.g., 240000000 for 240 MHz). Set at boot time.
  - ESP32/ESP32-S3: Supports up to 240 MHz
  - ESP32-C6: Supports up to 160 MHz
  - Set to `null` to use default frequency
- **`valid_gpio_pins`**: Array of GPIO pins safe to use
- **`reserved_pins`**: Array of pins that should NOT be used (flash, USB, etc.)
- **`notes`**: Object with pin-specific notes/warnings
- **`default_sensor_pins`**: Recommended pins for common sensors (-1 = not configured)
- **`i2c`**: Default I2C pins (scl/sda)

## Usage

1. Select your board configuration in `src/config.py`:

   ```python
   BOARD_CONFIG_FILE = "/boards/esp32s3_devkitc_1_n16r8v.json"
   ```

2. Deploy board configs to the ESP32:

   ```bash
   ./scripts/deploy_src.sh  # Automatically uploads board configs
   ```

3. The web interface will automatically show only available GPIO pins for your board when adding new relays.

## Adding a New Board

1. Create a new JSON file in this directory (e.g., `my_board.json`)
2. Follow the format above
3. Update `src/config.py` to reference your new board file
4. Deploy and test!

## Notes

- **Valid GPIO Pins**: Pins that are physically available and safe to use
- **Reserved Pins**: Pins used by flash, USB, or other critical functions (should not be used)
- **Strapping Pins**: Pins that affect boot behavior (use with caution)
- **Pin -1**: Indicates feature is disabled or not available
