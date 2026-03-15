"""
MicroPython module stubs for running ESP32 code on CPython.

Provides just enough of each module to boot and run the application.
Sensor values are driven by sim_config.json (reloaded periodically).
"""

import sys
import os
import json
import time as _time
import asyncio
import gc as _gc
import traceback
import types

# ---------------------------------------------------------------------------
# SimState: shared simulated sensor values, loaded from sim_config.json
# ---------------------------------------------------------------------------

class SimState:
    """Singleton that holds simulated sensor values from sim_config.json."""

    _instance = None
    _RELOAD_INTERVAL = 5  # seconds

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = None
            cls._instance._last_load = 0
            cls._instance._data = {
                "temperature": 25.0,
                "humidity": 50.0,
                "light_level": 2000,
                "switch_state": False,
                "reset_switch_state": False,
            }
        return cls._instance

    def set_config_path(self, path):
        self._config_path = path
        self._reload()

    def _reload(self):
        if self._config_path is None:
            return
        try:
            with open(self._config_path, "r") as f:
                self._data = json.load(f)
            self._last_load = _time.time()
        except Exception:
            pass  # keep previous values

    def get(self, key, default=None):
        if _time.time() - self._last_load > self._RELOAD_INTERVAL:
            self._reload()
        return self._data.get(key, default)


_sim = SimState()

# ---------------------------------------------------------------------------
# machine module
# ---------------------------------------------------------------------------

def _build_machine_module():
    mod = types.ModuleType("machine")

    # Constants
    mod.PWRON_RESET = 1
    mod.HARD_RESET = 2
    mod.WDT_RESET = 3
    mod.DEEPSLEEP_RESET = 4
    mod.SOFT_RESET = 5

    _current_freq = 240_000_000

    def freq(val=None):
        nonlocal _current_freq
        if val is None:
            return _current_freq
        _current_freq = val
        print(f"[EMU] CPU frequency set to {val // 1_000_000} MHz")

    mod.freq = freq
    mod.reset_cause = lambda: mod.PWRON_RESET

    def reset():
        print("[EMU] machine.reset() called – exiting emulator")
        os._exit(0)

    mod.reset = reset

    class Pin:
        IN = 0
        OUT = 1
        PULL_UP = 2

        def __init__(self, pin_num, mode=None, pull=None):
            self.pin_num = pin_num
            self.mode = mode
            self._value = 0

        def value(self, val=None):
            if val is None:
                # For input pins used as switches, return from SimState
                return self._value
            old = self._value
            self._value = val
            if old != val:
                state = "HIGH" if val else "LOW"
                print(f"[GPIO] Pin {self.pin_num} -> {state}")

    mod.Pin = Pin

    class ADC:
        ATTN_11DB = 3

        def __init__(self, pin):
            self.pin = pin

        def atten(self, val):
            pass

        def read(self):
            return _sim.get("light_level", 2000)

    mod.ADC = ADC

    class RTC:
        def __init__(self):
            pass

        def datetime(self, val=None):
            if val is None:
                t = _time.localtime()
                return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_wday,
                        t.tm_hour, t.tm_min, t.tm_sec, 0)
            # setter is a no-op on CPython (system clock is authoritative)

    mod.RTC = RTC

    class I2C:
        def __init__(self, bus=0, scl=None, sda=None, freq=100_000):
            pass

        def writeto(self, addr, buf):
            pass

        def readfrom(self, addr, nbytes):
            return bytes(nbytes)

    mod.I2C = I2C

    return mod

# ---------------------------------------------------------------------------
# network module
# ---------------------------------------------------------------------------

def _build_network_module():
    mod = types.ModuleType("network")
    mod.STA_IF = 0
    mod.AP_IF = 1

    class WLAN:
        def __init__(self, interface):
            self._interface = interface
            self._active = True
            self._connected = interface == mod.STA_IF

        def active(self, val=None):
            if val is None:
                return self._active
            self._active = val

        def connect(self, ssid=None, password=None):
            self._connected = True
            print(f"[EMU] WiFi connect to '{ssid}' (simulated)")

        def disconnect(self):
            pass

        def isconnected(self):
            return self._connected

        def ifconfig(self):
            return ("127.0.0.1", "255.255.255.0", "127.0.0.1", "8.8.8.8")

        def scan(self):
            return [
                (b"EmulatorNet", b"\x00" * 6, 6, -45, 3, False),
                (b"Neighbor_WiFi", b"\x00" * 6, 1, -72, 3, False),
            ]

        def config(self, key=None, **kwargs):
            if key == "essid":
                return "EmulatorWiFi"
            if key == "mac":
                return b"\xDE\xAD\xBE\xEF\x00\x01"
            if kwargs:
                pass  # ignore AP config calls

        def status(self, key=None):
            if key == "rssi":
                return -42
            return 0

    mod.WLAN = WLAN

    def hostname(name=None):
        if name:
            print(f"[EMU] Hostname set to: {name}")

    mod.hostname = hostname
    return mod

# ---------------------------------------------------------------------------
# esp32 module
# ---------------------------------------------------------------------------

def _build_esp32_module():
    mod = types.ModuleType("esp32")
    mod.raw_temperature = lambda: 120.0  # Fahrenheit (~49C)
    return mod

# ---------------------------------------------------------------------------
# neopixel module
# ---------------------------------------------------------------------------

def _build_neopixel_module():
    mod = types.ModuleType("neopixel")

    class NeoPixel:
        def __init__(self, pin, count):
            self._pixels = [(0, 0, 0)] * count

        def __setitem__(self, idx, color):
            self._pixels[idx] = color

        def __getitem__(self, idx):
            return self._pixels[idx]

        def write(self):
            r, g, b = self._pixels[0]
            if r == 0 and g == 0 and b == 0:
                return  # don't spam off messages
            print(f"[LED] ({r}, {g}, {b})")

    mod.NeoPixel = NeoPixel
    return mod

# ---------------------------------------------------------------------------
# onewire + ds18x20 modules
# ---------------------------------------------------------------------------

def _build_onewire_module():
    mod = types.ModuleType("onewire")

    class OneWire:
        def __init__(self, pin):
            pass

    mod.OneWire = OneWire
    return mod


def _build_ds18x20_module():
    mod = types.ModuleType("ds18x20")
    _FAKE_ROM = b"\x28\x01\x02\x03\x04\x05\x06\x07"

    class DS18X20:
        def __init__(self, ow):
            pass

        def scan(self):
            return [_FAKE_ROM]

        def convert_temp(self):
            pass

        def read_temp(self, rom):
            return _sim.get("temperature", 25.0)

    mod.DS18X20 = DS18X20
    return mod

# ---------------------------------------------------------------------------
# aht21 stub (replaces the real I2C-based AHT21 driver)
# ---------------------------------------------------------------------------

def _build_aht21_module():
    mod = types.ModuleType("aht21")

    class AHT21:
        def __init__(self, scl_pin, sda_pin, addr=0x38):
            pass

        def Is_Calibrated(self):
            return True

        def T(self):
            return _sim.get("temperature", 25.0)

        def RH(self):
            return _sim.get("humidity", 50.0)

    mod.AHT21 = AHT21
    return mod

# ---------------------------------------------------------------------------
# ntptime module
# ---------------------------------------------------------------------------

def _build_ntptime_module():
    mod = types.ModuleType("ntptime")
    mod.host = "pool.ntp.org"

    def settime():
        print("[EMU] NTP settime (no-op, using system clock)")

    mod.settime = settime
    return mod

# ---------------------------------------------------------------------------
# urequests module
# ---------------------------------------------------------------------------

def _build_urequests_module():
    mod = types.ModuleType("urequests")

    class _Response:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

        def close(self):
            pass

    def get(url, **kwargs):
        # Return canned timezone response for WorldTimeAPI
        if "worldtimeapi.org" in url:
            # Try to get the real local timezone offset
            try:
                local_offset = _time.timezone if _time.daylight == 0 else _time.altzone
                offset_seconds = -local_offset  # Python's timezone is seconds west of UTC
                sign = "+" if offset_seconds >= 0 else "-"
                hours = abs(offset_seconds) // 3600
                minutes = (abs(offset_seconds) % 3600) // 60
                offset_str = f"{sign}{hours:02d}:{minutes:02d}"
            except Exception:
                offset_str = "+00:00"
                offset_seconds = 0

            try:
                import zoneinfo
                tz_name = str(_time.tzname[0])
            except Exception:
                tz_name = "Local"

            body = json.dumps({
                "timezone": tz_name,
                "utc_offset": offset_str,
            })
            return _Response(200, body)

        return _Response(404, "")

    mod.get = get
    return mod

# ---------------------------------------------------------------------------
# webrepl, mdns, micropython, webrepl_cfg modules
# ---------------------------------------------------------------------------

def _build_webrepl_module():
    mod = types.ModuleType("webrepl")

    def start(**kwargs):
        print("[EMU] WebREPL start (no-op)")

    mod.start = start
    return mod


def _build_mdns_module():
    mod = types.ModuleType("mdns")

    class Server:
        def start(self, hostname, description=""):
            print(f"[EMU] mDNS started: {hostname}.local")

    mod.Server = Server
    return mod


def _build_micropython_module():
    mod = types.ModuleType("micropython")
    mod.const = lambda x: x
    return mod


def _build_webrepl_cfg_module():
    mod = types.ModuleType("webrepl_cfg")
    mod.PASS = "emulator"
    return mod

# ---------------------------------------------------------------------------
# Patch CPython stdlib to add MicroPython-specific functions
# ---------------------------------------------------------------------------

def _patch_time():
    _time.ticks_ms = lambda: int(_time.time() * 1000) & 0x3FFFFFFF
    _time.ticks_diff = lambda a, b: (a - b)
    _time.sleep_ms = lambda ms: _time.sleep(ms / 1000)


def _patch_gc():
    _gc.mem_free = lambda: 200_000
    _gc.mem_alloc = lambda: 120_000


def _patch_sys():
    def print_exception(e, file=None):
        traceback.print_exception(type(e), e, e.__traceback__, file=file or sys.stderr)

    sys.print_exception = print_exception


# ---------------------------------------------------------------------------
# Switch pin simulation: make input pins return SimState values
# ---------------------------------------------------------------------------

def _patch_switch_pins():
    """Hook into machine.Pin so input pins return sim_config values.

    sensors.py reads switches via pin.value() == 0 (active low).
    We return 0 when sim says True (pressed), 1 when False (not pressed).
    """
    machine_mod = sys.modules["machine"]
    _OrigPin = machine_mod.Pin

    class SimPin(_OrigPin):
        # Map of pin numbers to SimState keys (set after sensor init)
        _switch_map = {}

        def value(self, val=None):
            if val is not None:
                return super().value(val)
            # Check if this pin is mapped to a simulated switch
            key = self._switch_map.get(self.pin_num)
            if key is not None:
                pressed = _sim.get(key, False)
                return 0 if pressed else 1  # active low
            return super().value()

        @classmethod
        def register_switch(cls, pin_num, sim_key):
            cls._switch_map[pin_num] = sim_key

    machine_mod.Pin = SimPin


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_all(sim_config_path=None):
    """Register all stub modules and patches. Call before importing any src/ code."""

    if sim_config_path:
        _sim.set_config_path(sim_config_path)

    # Register stub modules
    sys.modules["machine"] = _build_machine_module()
    sys.modules["network"] = _build_network_module()
    sys.modules["esp32"] = _build_esp32_module()
    sys.modules["neopixel"] = _build_neopixel_module()
    sys.modules["onewire"] = _build_onewire_module()
    sys.modules["ds18x20"] = _build_ds18x20_module()
    sys.modules["aht21"] = _build_aht21_module()
    sys.modules["ntptime"] = _build_ntptime_module()
    sys.modules["urequests"] = _build_urequests_module()
    sys.modules["ujson"] = json
    sys.modules["uasyncio"] = asyncio
    sys.modules["micropython"] = _build_micropython_module()
    sys.modules["webrepl"] = _build_webrepl_module()
    sys.modules["webrepl_cfg"] = _build_webrepl_cfg_module()
    sys.modules["mdns"] = _build_mdns_module()

    # Patch stdlib modules
    _patch_time()
    _patch_gc()
    _patch_sys()

    # Set up switch pin simulation
    _patch_switch_pins()

    print("[EMU] All MicroPython stubs registered")
