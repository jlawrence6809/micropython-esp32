# MicroPython ESP32-S3 Setup

This folder contains scripts to flash MicroPython onto the ESP32-S3-DevKitC-1-N16R8V board.

## Board Specifications

- **Board**: ESP32-S3-DevKitC-1-N16R8V
- **Flash**: 16MB
- **PSRAM**: 8MB
- **USB**: Native USB support (USB-OTG)

## Quick Start

### 1. Install Dependencies

```bash
pip install esptool
```

### 2. Download MicroPython Firmware

```bash
./download_firmware.sh
```

This will download the latest stable MicroPython firmware for ESP32-S3.

### 3. Flash MicroPython

Connect your ESP32-S3 board via USB, then run:

```bash
./flash.sh
```

The script will:

- Detect the USB port automatically
- Erase the flash
- Flash MicroPython firmware
- Reset the board

### 4. Connect to REPL

After flashing, connect to the MicroPython REPL:

```bash
./monitor.sh
```

Or manually:

```bash
screen /dev/tty.usbmodem* 115200
```

Press Ctrl+A, then K, then Y to exit screen.

## Manual Flashing

If the automatic script doesn't work, you can flash manually:

```bash
# Find your device port
ls /dev/tty.usb*

# Erase flash
esptool.py --chip esp32s3 --port /dev/tty.usbmodem* erase_flash

# Flash firmware
esptool.py --chip esp32s3 --port /dev/tty.usbmodem* write_flash -z 0 firmware/ESP32_GENERIC_S3-*.bin
```

## Webrepl

It doesn't work over https, and opening the page will automatically redirect to https unless it is opened in an incognito window:

http://micropython.org/webrepl/#10.0.0.58:8266

## Testing MicroPython

Once connected to the REPL, try:

```python
import machine
import sys

# Check system info
print(sys.implementation)
print(sys.platform)

# Blink the onboard LED (GPIO48 on DevKitC-1)
led = machine.Pin(48, machine.Pin.OUT)
led.on()
led.off()
```

## Troubleshooting

### Port Not Found

- Make sure the board is connected via USB
- Try pressing the BOOT button while connecting
- Check if the USB cable supports data transfer (not just charging)

### Permission Denied

On macOS/Linux, you may need to add your user to dialout group or use sudo.

### Board Not Entering Flash Mode

1. Hold BOOT button
2. Press and release RESET button
3. Release BOOT button
4. Try flashing again

## Resources

- [MicroPython Documentation](https://docs.micropython.org/)
- [ESP32-S3 Quick Reference](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [ESP32-S3-DevKitC-1 Datasheet](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html)
