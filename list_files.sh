#!/bin/bash

# List files on the MicroPython board
# Usage: ./list_files.sh [port]

# Auto-detect port if not provided
if [ -n "$1" ]; then
    PORT="$1"
else
    PORT=$(ls /dev/tty.usbmodem* 2>/dev/null | head -n 1)
    if [ -z "$PORT" ]; then
        PORT=$(ls /dev/tty.usbserial* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -n 1)
    fi
fi

if [ -z "$PORT" ]; then
    echo "Error: No USB device found"
    exit 1
fi

# Check if mpremote is installed
if ! command -v mpremote &> /dev/null; then
    echo "Error: mpremote not found"
    echo "Install with: pip install -r requirements.txt"
    exit 1
fi

echo "Listing files on board at $PORT..."
echo ""

mpremote connect "$PORT" fs ls

