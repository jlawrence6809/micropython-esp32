# main.py - MicroPython Automation Platform
# This file runs automatically after boot.py

import uasyncio as asyncio
from web_server import WebServer
import sys

async def main():
    print("Starting main.py...")
    
    # Start Web Server
    server = WebServer()
    asyncio.create_task(server.start())
    
    print("System started!")
    
    # Main loop
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
        # Clean exit (allows REPL to take over without hard crash state if desired)
        sys.exit(0)
    except Exception as e:
        print(f"Error in main: {e}")
