#!/bin/bash

# Upload a Python file to MicroPython board
# Usage: ./upload.sh <file.py> [destination] [port]
# Example: ./upload.sh my_script.py main.py

if [ -z "$1" ]; then
    echo "Usage: ./upload.sh <file.py> [destination] [port]"
    echo ""
    echo "Examples:"
    echo "  ./upload.sh main.py              # Upload as main.py"
    echo "  ./upload.sh test.py main.py      # Upload test.py as main.py"
    echo "  ./upload.sh config.py            # Upload as config.py"
    exit 1
fi

SOURCE_FILE="$1"
DEST_FILE="${2:-$1}"  # Default to same name if not specified

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: File not found: $SOURCE_FILE"
    exit 1
fi

# Auto-detect port if not provided
if [ -n "$3" ]; then
    PORT="$3"
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

echo "Uploading $SOURCE_FILE to board as $DEST_FILE..."
mpremote connect "$PORT" fs cp "$SOURCE_FILE" ":$DEST_FILE"
echo "Done!"

echo ""
echo "File uploaded. You can:"
echo "  1. Reset the board to run $DEST_FILE"
echo "  2. Or run ./monitor.sh and manually import it"

