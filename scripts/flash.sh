#!/bin/bash

# Flash MicroPython to ESP32-S3-DevKitC-1-N16R8V
# Usage: ./flash.sh [port]
# Example: ./flash.sh /dev/tty.usbmodem101

set -e

# Resolve project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

BAUD_RATE="460800"

FIRMWARE_DIR="$PROJECT_ROOT/firmware"

# ESP32-S3
# CHIP="esp32s3"
# FLASH_ADDR="0x0"
# FIRMWARE_FILE=$(ls "$FIRMWARE_DIR"/ESP32_GENERIC_S3-*.bin 2>/dev/null | head -n 1)

# ESP32 (regular ESP32)
CHIP="esp32"
FLASH_ADDR="0x1000"
FIRMWARE_FILE=$(ls "$FIRMWARE_DIR"/ESP32_GENERIC-*.bin 2>/dev/null | head -n 1)

if [ -z "$FIRMWARE_FILE" ]; then
    echo "Error: Firmware not found in $FIRMWARE_DIR/"
    echo "Run ./scripts/download_firmware.sh first"
    exit 1
fi

# Source ESP-IDF environment to get esptool.py (if available)
if [ -f "/Users/jeremy/code/esp-idf/export.sh" ]; then
    export IDF_PATH="/Users/jeremy/code/esp-idf"
    source "$IDF_PATH/export.sh" > /dev/null 2>&1
fi

# Check if esptool is available
if ! command -v esptool.py &> /dev/null; then
    echo "Error: esptool.py not found"
    echo "Install with: pip install esptool"
    echo "Or source ESP-IDF: source /Users/jeremy/code/esp-idf/export.sh"
    exit 1
fi

# Use provided port or auto-detect
if [ -n "$1" ]; then
    PORT="$1"
else
    # Auto-detect port (prefer tty.usbmodem for ESP32-S3)
    PORT=$(ls /dev/tty.usbmodem* 2>/dev/null | head -n 1)
    if [ -z "$PORT" ]; then
        PORT=$(ls /dev/tty.usbserial* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -n 1)
    fi
fi

if [ -z "$PORT" ]; then
    echo "Error: No USB device found"
    echo "Available ports:"
    ls /dev/tty.* 2>/dev/null || echo "None found"
    exit 1
fi

echo "Flashing $FIRMWARE_FILE to $PORT..."
echo ""

# Erase and flash
esptool.py --chip "$CHIP" --port "$PORT" erase_flash
esptool.py --chip "$CHIP" --port "$PORT" --baud "$BAUD_RATE" write_flash -z "$FLASH_ADDR" "$FIRMWARE_FILE"

echo ""
echo "Done! Run ./scripts/monitor.sh to connect to the REPL"

