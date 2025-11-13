#!/bin/bash

# Check for ESP32-S3 USB port

echo "Looking for ESP32-S3 USB devices..."
echo ""

# Check for tty devices
echo "TTY devices:"
ls -la /dev/tty.usb* 2>/dev/null || echo "  None found"
echo ""

# Check for cu devices
echo "CU devices:"
ls -la /dev/cu.usb* 2>/dev/null || echo "  None found"
echo ""

if ls /dev/tty.usb* /dev/cu.usb* &>/dev/null; then
    echo "✓ Device found! You can run ./monitor.sh now"
else
    echo "✗ No devices found"
    echo ""
    echo "Try:"
    echo "  1. Unplug the USB cable"
    echo "  2. Wait 2 seconds"
    echo "  3. Plug it back in"
    echo "  4. Run this script again"
fi

