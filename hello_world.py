"""
Simple MicroPython test script for ESP32-S3-DevKitC-1

This script can be uploaded to the board and run to test basic functionality.
"""

import machine
import time
import sys

def main():
    """Main function to test the ESP32-S3 board"""
    
    print("=" * 50)
    print("ESP32-S3 MicroPython Test")
    print("=" * 50)
    print()
    
    # System information
    print("System Information:")
    print(f"  Platform: {sys.platform}")
    print(f"  Version: {sys.version}")
    print(f"  Implementation: {sys.implementation}")
    print()
    
    # CPU frequency
    freq = machine.freq()
    print(f"CPU Frequency: {freq / 1_000_000} MHz")
    print()
    
    # Test onboard RGB LED (GPIO48 on DevKitC-1)
    print("Testing onboard LED (GPIO48)...")
    led = machine.Pin(48, machine.Pin.OUT)
    
    # Blink 5 times
    for i in range(5):
        print(f"  Blink {i+1}/5")
        led.on()
        time.sleep(0.3)
        led.off()
        time.sleep(0.3)
    
    print()
    print("✅ Test complete!")
    print()
    print("Try these next:")
    print("  - Connect sensors to GPIO pins")
    print("  - Test WiFi connectivity")
    print("  - Use the PSRAM for large data structures")

if __name__ == "__main__":
    main()

