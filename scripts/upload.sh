#!/bin/bash

# Upload a Python file to MicroPython board
# Usage: ./upload.sh <file.py> [destination]
# Example: ./upload.sh my_script.py main.py

# Resolve project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

if [ -z "$1" ]; then
    echo "Usage: ./scripts/upload.sh <file.py> [destination]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/upload.sh src/main.py            # Upload src/main.py as main.py"
    echo "  ./scripts/upload.sh src/test.py main.py    # Upload src/test.py as main.py"
    exit 1
fi

SOURCE_FILE="$1"
# If file doesn't exist, try looking in src/
if [ ! -f "$SOURCE_FILE" ] && [ -f "$PROJECT_ROOT/src/$SOURCE_FILE" ]; then
    SOURCE_FILE="$PROJECT_ROOT/src/$SOURCE_FILE"
fi

DEST_FILE="${2:-$(basename "$SOURCE_FILE")}"  # Default to same filename

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: File not found: $SOURCE_FILE"
    exit 1
fi

echo "Uploading $SOURCE_FILE to board as $DEST_FILE..."
"$SCRIPT_DIR/remote.sh" fs cp "$SOURCE_FILE" ":$DEST_FILE"
echo "Done!"

echo ""
echo "File uploaded. You can:"
echo "  1. Reset the board to run $DEST_FILE"
echo "  2. Or run ./scripts/monitor.sh and manually import it"

