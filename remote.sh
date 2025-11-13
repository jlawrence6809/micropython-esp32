#!/bin/bash

# Runs a command on the MicroPython board via mpremote
# Usage: ./remote.sh <command> [args...]
# Examples:
#   ./remote.sh fs ls
#   ./remote.sh fs cat boot.py
#   ./remote.sh exec "import os; print(os.listdir())"
#   ./remote.sh repl

if [ $# -eq 0 ]; then
    echo "Usage: ./remote.sh <command> [args...]"
    echo ""
    echo "Examples:"
    echo "  ./remote.sh fs ls              # List files"
    echo "  ./remote.sh fs cat boot.py     # Show file contents"
    echo "  ./remote.sh exec 'print(123)'  # Execute Python code"
    echo "  ./remote.sh repl               # Start REPL"
    exit 1
fi

# Check if mpremote is installed
if ! command -v mpremote &> /dev/null; then
    echo "Error: mpremote not found"
    echo "Install with: pip install -r requirements.txt"
    exit 1
fi

# Auto-detect port
PORT=$(ls /dev/tty.usbmodem* 2>/dev/null | head -n 1)
if [ -z "$PORT" ]; then
    PORT=$(ls /dev/tty.usbserial* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -n 1)
fi

if [ -z "$PORT" ]; then
    echo "Error: No USB device found"
    exit 1
fi

# Run mpremote with all arguments passed through
mpremote connect "$PORT" "$@"

