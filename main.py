# main.py - Example MicroPython application
# This file runs automatically after boot.py

import machine
import time

print("Starting main.py...")

# Blink the onboard LED 3 times on startup
led = machine.Pin(48, machine.Pin.OUT)

for i in range(3):
    print(f"Blink {i+1}")
    led.on()
    time.sleep(0.2)
    led.off()
    time.sleep(0.2)

print("Startup complete!")
print("Ready for commands.")

