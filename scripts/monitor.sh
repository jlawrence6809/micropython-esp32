#!/bin/bash

# Connect to MicroPython REPL with auto-reconnect
# Usage: ./scripts/monitor.sh [port]
# Example: ./scripts/monitor.sh /dev/tty.usbmodem101
#
# Press Ctrl+C to exit the monitor loop

BAUD_RATE=115200
FIXED_PORT="$1"

detect_port() {
    if [ -n "$FIXED_PORT" ]; then
        # If user specified a port, only use that one
        if [ -e "$FIXED_PORT" ]; then
            echo "$FIXED_PORT"
        fi
    else
        # Auto-detect port (prefer tty.usbmodem for ESP32-S3)
        local port=$(ls /dev/tty.usbmodem* 2>/dev/null | head -n 1)
        if [ -z "$port" ]; then
            port=$(ls /dev/tty.usbserial* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -n 1)
        fi
        echo "$port"
    fi
}

wait_for_port() {
    echo "Waiting for device..."
    while true; do
        PORT=$(detect_port)
        if [ -n "$PORT" ]; then
            # Small delay to let the port stabilize after appearing
            sleep 0.5
            return 0
        fi
        sleep 0.5
    done
}

cleanup() {
    echo ""
    echo "Monitor stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "=== MicroPython Serial Monitor (auto-reconnect) ==="
echo "Press Ctrl+C to exit"
echo ""

while true; do
    PORT=$(detect_port)
    
    if [ -z "$PORT" ]; then
        wait_for_port
    fi
    
    echo "----------------------------------------"
    echo "[$(date '+%H:%M:%S')] Connecting to $PORT at $BAUD_RATE baud"
    echo "----------------------------------------"
    
    # Use cat for simple monitoring (no interactive REPL but captures everything)
    # Or use screen for interactive mode
    if command -v picocom &> /dev/null; then
        # picocom handles reconnects better and shows all output
        picocom -b "$BAUD_RATE" --imap lfcrlf "$PORT" 2>/dev/null
    else
        # Fallback to screen
        screen "$PORT" "$BAUD_RATE"
    fi
    
    echo ""
    echo "[$(date '+%H:%M:%S')] Connection lost - will reconnect automatically..."
    sleep 1
done

