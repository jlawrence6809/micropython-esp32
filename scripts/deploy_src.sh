#!/bin/bash

# Deploy all source files to ESP32
# Usage: ./scripts/deploy_src.sh

set -e

# Resolve project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
SRC_DIR="$PROJECT_ROOT/src"
BOARDS_DIR="$PROJECT_ROOT/boards"
REMOTE_SCRIPT="$SCRIPT_DIR/remote.sh"

# Files to exclude from upload
EXCLUDE_FILES=(
    "config.example.py"
)

echo "=== Deploying Source Code ==="
echo "Source directory: $SRC_DIR"

if [ ! -d "$SRC_DIR" ]; then
    echo "Error: Source directory not found at $SRC_DIR"
    exit 1
fi

# Check connection first
echo "Checking connection..."
"$REMOTE_SCRIPT" exec "import os; print('Connected to:', os.uname().machine)" || exit 1

echo ""
echo "Uploading source files..."

cd "$SRC_DIR"
for file in *.py; do
    if [ -f "$file" ]; then
        # Check if file is in exclude list
        skip=0
        for excluded in "${EXCLUDE_FILES[@]}"; do
            if [ "$file" == "$excluded" ]; then
                skip=1
                break
            fi
        done

        if [ $skip -eq 1 ]; then
            echo "Skipping $file (excluded)"
            continue
        fi

        echo "Uploading $file..."
        "$REMOTE_SCRIPT" fs cp "$file" ":$file"
    fi
done

echo ""
echo "Uploading board configurations..."

# Create /boards directory on device
"$REMOTE_SCRIPT" fs mkdir :/boards 2>/dev/null || true

cd "$BOARDS_DIR"
for file in *.json; do
    if [ -f "$file" ]; then
        echo "Uploading boards/$file..."
        "$REMOTE_SCRIPT" fs cp "$file" ":/boards/$file"
    fi
done

echo ""
echo "Deployment complete!"
echo "Restarting main.py..."

# Soft restart: re-import and run main.py without rebooting the hardware
"$REMOTE_SCRIPT" exec "
import sys
# Remove main from sys.modules to force reload
if 'main' in sys.modules:
    del sys.modules['main']
if 'web_server' in sys.modules:
    del sys.modules['web_server']
if 'relays' in sys.modules:
    del sys.modules['relays']

# Now import and run main
import main
import uasyncio as asyncio
asyncio.run(main.main())
" &

echo "Application restarted in background!"
echo "Note: The mpremote connection will stay active. Press Ctrl+C to exit if needed."
