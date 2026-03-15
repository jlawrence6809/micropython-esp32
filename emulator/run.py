#!/usr/bin/env python3
"""
ESP32 MicroPython Emulator Runner

Boots the application on CPython with stubbed hardware modules.
Sensor values are driven by emulator/sim_config.json (edit while running).

Usage:
    python emulator/run.py              # default port 8080
    python emulator/run.py --port 3000  # custom port
"""

import argparse
import builtins
import json
import os
import sys
import shutil

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EMULATOR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EMULATOR_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
FS_DIR = os.path.join(EMULATOR_DIR, "fs")
SIM_CONFIG = os.path.join(EMULATOR_DIR, "sim_config.json")

# ---------------------------------------------------------------------------
# Set up the virtual filesystem (emulator/fs/)
# ---------------------------------------------------------------------------

def setup_fs():
    """Create emulator/fs/ with default files if it doesn't exist."""
    os.makedirs(FS_DIR, exist_ok=True)

    # config.json
    config_path = os.path.join(FS_DIR, "config.json")
    if not os.path.exists(config_path):
        config = {
            "wifi": {"ssid": "EmulatorWiFi", "password": "emulator123"},
            "hostname": "esp32-emu",
            "board": "esp32s3_devkitc_1_n16r8v.json",
            "timezone": {"name": "Local", "offset_seconds": 0},
            "sensor_pins": {
                "i2c_scl": 1,
                "i2c_sda": 2,
                "ds18b20": 38,
                "photo_sensor": 4,
                "light_switch": 5,
                "reset_switch": 6,
            },
        }
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"[EMU] Created {config_path}")

    # relays.json
    relays_path = os.path.join(FS_DIR, "relays.json")
    if not os.path.exists(relays_path):
        with open(relays_path, "w") as f:
            json.dump({"relays": []}, f)
        print(f"[EMU] Created {relays_path}")

    # boards/ symlink
    boards_link = os.path.join(FS_DIR, "boards")
    if not os.path.exists(boards_link):
        boards_src = os.path.join(PROJECT_ROOT, "boards")
        os.symlink(boards_src, boards_link)
        print(f"[EMU] Symlinked boards/ -> {boards_src}")

    # www/ symlink (optional – only if preact build exists)
    www_link = os.path.join(FS_DIR, "www")
    if not os.path.exists(www_link):
        # Try common build output dirs
        for candidate in ["preact/build", "preact/dist"]:
            build_dir = os.path.join(PROJECT_ROOT, candidate)
            if os.path.isdir(build_dir):
                os.symlink(build_dir, www_link)
                print(f"[EMU] Symlinked www/ -> {build_dir}")
                break

# ---------------------------------------------------------------------------
# Monkey-patch file operations for ESP32 absolute paths
# ---------------------------------------------------------------------------

def patch_file_ops():
    """ESP32 code uses absolute paths like /boards/file.json and /www/index.html.
    In the emulator, we strip the leading / so they resolve relative to fs/.
    """
    _orig_open = builtins.open
    _orig_stat = os.stat
    _orig_listdir = os.listdir
    _orig_statvfs = os.statvfs

    # Only rewrite ESP32-style absolute paths (short paths like /boards/, /www/)
    # Leave real filesystem absolute paths alone (e.g., /Users/...)
    _ESP32_PREFIXES = ("/boards/", "/boards", "/www/", "/www")

    def _strip(path):
        if isinstance(path, str):
            for prefix in _ESP32_PREFIXES:
                if path.startswith(prefix):
                    return path.lstrip("/")
            # Also handle bare "/" for statvfs('/')
            if path == "/":
                return "."
        return path

    def emu_open(path, *args, **kwargs):
        return _orig_open(_strip(path), *args, **kwargs)

    def emu_stat(path, *args, **kwargs):
        return _orig_stat(_strip(path), *args, **kwargs)

    def emu_listdir(path=".", *args, **kwargs):
        return _orig_listdir(_strip(path), *args, **kwargs)

    def emu_statvfs(path, *args, **kwargs):
        return _orig_statvfs(_strip(path), *args, **kwargs)

    builtins.open = emu_open
    os.stat = emu_stat
    os.listdir = emu_listdir
    os.statvfs = emu_statvfs

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ESP32 MicroPython Emulator")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default: 8080)")
    args = parser.parse_args()

    print("=" * 50)
    print("  ESP32 MicroPython Emulator")
    print("=" * 50)

    # 1. Set up virtual filesystem
    setup_fs()

    # 2. Change to fs/ so relative paths work
    os.chdir(FS_DIR)

    # 3. Patch file operations for absolute paths
    patch_file_ops()

    # 4. Register all MicroPython stubs
    sys.path.insert(0, os.path.join(EMULATOR_DIR))
    from stubs import register_all
    register_all(sim_config_path=SIM_CONFIG)

    # 5. Add src/ to path
    sys.path.insert(0, SRC_DIR)

    # 6. Register switch pin mappings (must happen after stubs are loaded)
    import machine
    # These pin numbers match the default sensor_pins in config.json
    machine.Pin.register_switch(5, "switch_state")
    machine.Pin.register_switch(6, "reset_switch_state")

    # 7. Boot the application (mirrors boot.py)
    print("\n" + "=" * 50)
    print("  Booting application...")
    print("=" * 50 + "\n")

    from instances import instances
    instances.initialize()

    # Skip real WiFi — stub already reports connected
    # Just set up the state that boot.py normally sets
    instances.board.set_cpu_frequency()
    instances.led.set_state("booting")

    # Simulate successful WiFi connection
    instances.wifi.mode = "sta"
    instances.led.set_state("normal")

    # Time sync — use system clock (already accurate on dev machine)
    instances.time_sync.is_synced = True
    instances.time_sync.last_sync_time = int(_time.time())

    # Load timezone from config
    offset = instances.config.get_timezone_offset_seconds()
    instances.time_sync.TIMEZONE_OFFSET = offset

    # Override web server port
    instances.server.port = args.port

    print(f"\n[EMU] Web server will start on http://localhost:{args.port}")
    print(f"[EMU] Edit {SIM_CONFIG} to change sensor values\n")

    # 8. Run the async main loop (mirrors main.py)
    import asyncio

    async def run():
        # Import main module's functions
        from main import automation_loop

        # Start all async tasks
        asyncio.create_task(instances.led.run())
        asyncio.create_task(instances.server.start())
        asyncio.create_task(automation_loop())

        print("[EMU] System started!")

        # Keep running
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[EMU] Stopped by user")
        sys.exit(0)


# Need time module before stubs are loaded
import time as _time

if __name__ == "__main__":
    main()
