#!/bin/bash

# Connect to MicroPython REPL
# Usage: ./scripts/monitor.sh [port]
# Example: ./scripts/monitor.sh /dev/tty.usbmodem101

BAUD_RATE=115200

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

echo "Connecting to $PORT at $BAUD_RATE baud"
echo "Press Ctrl+A, then K, then Y to exit"
echo ""

screen "$PORT" "$BAUD_RATE"

