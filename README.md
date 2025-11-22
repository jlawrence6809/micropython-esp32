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
./scripts/download_firmware.sh
```

This will download the latest stable MicroPython firmware for ESP32-S3.

### 3. Flash MicroPython

Connect your ESP32-S3 board via USB, then run:

```bash
./scripts/flash.sh
```

The script will:

- Detect the USB port automatically
- Erase the flash
- Flash MicroPython firmware
- Reset the board

### 4. Deploy Code

Deploy source code (Python scripts):

```bash
./scripts/deploy_src.sh
```

Deploy web interface (Preact app):

```bash
./scripts/deploy_web.sh
```

## Understanding MicroPython Execution

### Running vs. REPL

**Important:** MicroPython is single-threaded. It can either run your code (`main.py`) OR provide an interactive prompt (REPL), but not both at the same time.

- **Background Mode (Normal Operation)**:

  - When the board boots, it runs `boot.py` and then `main.py`.
  - Our `main.py` starts the Web Server and enters an infinite loop.
  - **The Web Server is ONLY active in this mode.**

- **REPL Mode (Interactive)**:
  - When you connect via `./scripts/monitor.sh` or `mpremote`, the board stops the running `main.py` (killing the web server) to give you a `>>>` prompt.
  - This is normal! It's how you debug.
  - To restart the server while in REPL, type:
    ```python
    import machine
    machine.reset()
    ```
    (This will disconnect your REPL session effectively).

### Viewing Logs Without Stopping Server

To see what the server is doing without killing it:

1.  Connect via USB.
2.  Run `./scripts/monitor.sh`.
3.  **Immediately** press the RESET button on the board.
4.  You will see the boot logs.
5.  **Do not press any keys** (Enter/Ctrl-C), or you will interrupt the server and drop into REPL.

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

## Resources

- [MicroPython Documentation](https://docs.micropython.org/)
- [ESP32-S3 Quick Reference](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [ESP32-S3-DevKitC-1 Datasheet](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html)
