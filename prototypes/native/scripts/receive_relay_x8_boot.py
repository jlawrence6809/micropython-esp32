#!/usr/bin/env python3
"""Receive-only attended Relay_X8 UART boot capture. stdout -> encrypted vault.
Executed by supervised SSH with settings stdin and frozen helper directory argv1.
No UART TX, reset pulse, profile mutation or arming. Bounds:360s/2MiB.
"""
import datetime
import json
import sys
import time
import termios
from pathlib import Path
import serial
sys.path.insert(0, sys.argv[1])
from remote_relay_x8_bootstrap import guard_port, require
c = json.load(sys.stdin)
require(c.get('purpose') == 'relay-x8-native-boot-capture' and c.get('loads_disconnected') is True, 'Unloaded attended capture required')
seconds = c['seconds']; require(type(seconds) is int and 1 <= seconds <= 360, 'Capture duration bound')
def report(**more):
    print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **more)), file=sys.stderr, flush=True)
with guard_port(c):
    port = serial.Serial(port=None, baudrate=115200, timeout=.2, exclusive=True)
    port.dtr = False; port.rts = False; port.port = c['port']
    try:
        port.open(); attrs=termios.tcgetattr(port.fileno()); attrs[2]&=~termios.HUPCL
        termios.tcsetattr(port.fileno(),termios.TCSANOW,attrs)
        report(state='capturing', seconds=seconds, tx_bytes=0, reset_commands=0)
        end=time.monotonic()+seconds; count=0; tail=b''; ready=False
        while time.monotonic()<end and count<2*1024*1024:
            data=port.read(4096)
            if data:
                sys.stdout.buffer.write(data);sys.stdout.buffer.flush();count+=len(data)
                tail=(tail+data)[-4096:]
                if not ready and b'RUNTIME_READY ' in tail:
                    ready=True;end=min(end,time.monotonic()+10)
                    report(state='runtime_ready_observed')
        report(state='finished', bytes=count, runtime_ready_observed=ready, tx_bytes=0)
    finally:
        port.close();report(state='serial_closed', tx_bytes=0, reset_commands=0)
