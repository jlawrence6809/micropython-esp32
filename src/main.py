# main.py - MicroPython Automation Platform
# This file runs automatically after boot.py

import uasyncio as asyncio
from web_server import WebServer

async def main():
    print("Starting main.py...")
    
    # Start Web Server
    server = WebServer()
    asyncio.create_task(server.start())
    
    print("System started!")
    
    # Main loop
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped by user")
except Exception as e:
    print(f"Error in main: {e}")
