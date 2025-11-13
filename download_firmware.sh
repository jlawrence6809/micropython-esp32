#!/bin/bash

# Download the latest MicroPython firmware for ESP32-S3

set -e

FIRMWARE_DIR="firmware"
FIRMWARE_URL="https://micropython.org/resources/firmware/ESP32_GENERIC_S3-20231005-v1.21.0.bin"
FIRMWARE_FILE="ESP32_GENERIC_S3-20231005-v1.21.0.bin"

mkdir -p "$FIRMWARE_DIR"
cd "$FIRMWARE_DIR"

if [ -f "$FIRMWARE_FILE" ]; then
    echo "Firmware already exists: $FIRMWARE_FILE"
    echo "Delete it first to re-download"
    exit 0
fi

echo "Downloading MicroPython firmware for ESP32-S3..."
curl -L -O "$FIRMWARE_URL"

echo ""
echo "Download complete: $FIRMWARE_DIR/$FIRMWARE_FILE"
echo "Run ./flash.sh to flash the firmware"

