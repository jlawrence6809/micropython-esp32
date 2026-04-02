#!/bin/bash

# Provision a new ESP32 board from scratch: flash firmware, deploy code, config, and web UI.
# Usage: ./scripts/provision.sh [port] [config_dir]
#
# Examples:
#   ./scripts/provision.sh                                          # auto-detect port, no device config
#   ./scripts/provision.sh /dev/tty.usbserial-0001                  # specific port
#   ./scripts/provision.sh /dev/tty.usbserial-0001 genericboard     # with device config from device_configs/genericboard/

set -e

# Resolve project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
SRC_DIR="$PROJECT_ROOT/src"
BOARDS_DIR="$PROJECT_ROOT/boards"
PREACT_DIR="$PROJECT_ROOT/preact"
FIRMWARE_DIR="$PROJECT_ROOT/firmware"

# Board settings (uncomment the appropriate chip)
# ESP32-S3
# CHIP="esp32s3"
# FLASH_ADDR="0x0"
# FIRMWARE_FILE=$(ls "$FIRMWARE_DIR"/ESP32_GENERIC_S3-*.bin 2>/dev/null | head -n 1)

# ESP32 (original)
CHIP="esp32"
FLASH_ADDR="0x1000"
FIRMWARE_FILE=$(ls "$FIRMWARE_DIR"/ESP32_GENERIC-*.bin 2>/dev/null | head -n 1)

BAUD_FLASH="115200"  # Conservative baud rate; 460800 can be flaky on some USB-serial chips
BAUD_UPLOAD="115200"

# --- Parse arguments ---

PORT="${1:-}"
CONFIG_DIR_NAME="${2:-}"

if [ -z "$PORT" ]; then
    PORT=$(ls /dev/tty.usbmodem* 2>/dev/null | head -n 1)
    if [ -z "$PORT" ]; then
        PORT=$(ls /dev/tty.usbserial* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -n 1)
    fi
fi

if [ -z "$PORT" ]; then
    echo "Error: No USB device found. Pass port as first argument."
    exit 1
fi

if [ -z "$FIRMWARE_FILE" ]; then
    echo "Error: No firmware found in $FIRMWARE_DIR/"
    echo "Run ./scripts/download_firmware.sh first"
    exit 1
fi

AMPY="ampy --port $PORT --baud $BAUD_UPLOAD"

echo "============================================"
echo "Provisioning ESP32"
echo "============================================"
echo "Port:     $PORT"
echo "Chip:     $CHIP"
echo "Firmware: $(basename "$FIRMWARE_FILE")"
if [ -n "$CONFIG_DIR_NAME" ]; then
    echo "Config:   device_configs/$CONFIG_DIR_NAME/"
fi
echo ""

# --- Step 1: Flash firmware ---

echo "=== Step 1: Erase and flash firmware ==="
esptool.py --chip "$CHIP" --port "$PORT" erase_flash
esptool.py --chip "$CHIP" --port "$PORT" --baud "$BAUD_FLASH" write_flash -z "$FLASH_ADDR" "$FIRMWARE_FILE"
echo ""

# Wait for board to boot into MicroPython
sleep 3

# --- Step 2: Upload source files (boot.py and main.py last) ---

echo "=== Step 2: Upload source files ==="
cd "$SRC_DIR"
for file in *.py; do
    [ "$file" = "boot.py" ] || [ "$file" = "main.py" ] && continue
    echo "  $file"
    $AMPY put "$file" "/$file"
done
cd "$PROJECT_ROOT"
echo ""

# --- Step 3: Upload board configs ---

echo "=== Step 3: Upload board configs ==="
$AMPY mkdir /boards 2>/dev/null || true
for file in "$BOARDS_DIR"/*.json; do
    filename=$(basename "$file")
    echo "  boards/$filename"
    $AMPY put "$file" "/boards/$filename"
done
echo ""

# --- Step 4: Upload device config (if provided) ---

if [ -n "$CONFIG_DIR_NAME" ]; then
    CONFIG_DIR="$PROJECT_ROOT/device_configs/$CONFIG_DIR_NAME"
    if [ ! -d "$CONFIG_DIR" ]; then
        echo "Warning: device_configs/$CONFIG_DIR_NAME/ not found, skipping"
    else
        echo "=== Step 4: Upload device config ==="
        for file in "$CONFIG_DIR"/*.json; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                echo "  $filename"
                $AMPY put "$file" "/$filename"
            fi
        done
        echo ""
    fi
fi

# --- Step 5: Build and upload web UI ---

echo "=== Step 5: Build and upload web UI ==="
cd "$PREACT_DIR"

if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

npm run build 2>&1 | tail -5

BUILD_DIR="$PREACT_DIR/build"
STAGING_DIR=$(mktemp -d)

# Gzip assets
for file in "$BUILD_DIR"/index.html "$BUILD_DIR"/bundle.*.js "$BUILD_DIR"/bundle.*.css "$BUILD_DIR"/polyfills.*.js; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        gzip -c "$file" > "$STAGING_DIR/$filename.gz"
    fi
done

$AMPY mkdir /www 2>/dev/null || true
for file in "$STAGING_DIR"/*.gz; do
    filename=$(basename "$file")
    echo "  www/$filename"
    $AMPY put "$file" "/www/$filename"
done
rm -rf "$STAGING_DIR"

cd "$PROJECT_ROOT"
echo ""

# --- Step 6: Upload boot files (last!) ---

echo "=== Step 6: Upload boot files (last) ==="
echo "  main.py"
$AMPY put "$SRC_DIR/main.py" "/main.py"
echo "  boot.py"
$AMPY put "$SRC_DIR/boot.py" "/boot.py"
echo ""

# --- Done ---

echo "============================================"
echo "Provisioning complete!"
echo "============================================"
echo ""
echo "The board will now reboot and connect to WiFi."
echo "Check serial output with: ./scripts/monitor.sh"
echo ""
if [ -n "$CONFIG_DIR_NAME" ]; then
    echo "Device config: device_configs/$CONFIG_DIR_NAME/"
else
    echo "No device config was uploaded."
    echo "The board will start in AP mode for WiFi setup."
    echo "Connect to the AP and configure via the web UI."
fi
