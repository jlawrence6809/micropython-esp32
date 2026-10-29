#!/usr/bin/env python3
"""Run via SSH stdin on the attended peripheral host; stream ONLY to private vault.
Standard-library only: no remote packages/project files/services installed.
Opening and modem-line deassertion can reset hardware: isolated loads required.
No UART bytes transmitted, reset pulse, firmware/configuration write or arming.
Reader is bounded to 3600 s / 2 MiB; stderr carries capture lifecycle metadata.
"""
import array
import datetime
import fcntl
import json
import os
from pathlib import Path
import select
import sys
import termios
import time

port='/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0'
assert os.uname().nodename=='drallion','Wrong peripheral host'
tty=Path(port).resolve();assert str(tty).startswith('/dev/ttyUSB')
parents=Path('/sys/class/tty/'+tty.name+'/device').resolve().parents
usb=next(x for x in parents if (x/'idVendor').exists())
assert (usb/'idVendor').read_text().strip()=='1a86' and (usb/'idProduct').read_text().strip()=='7523'
def report(**data):
    print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),**data)),file=sys.stderr,flush=True)
fd=os.open(port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
try:
    fcntl.ioctl(fd,termios.TIOCEXCL)
    attrs=termios.tcgetattr(fd)
    attrs[0]=0;attrs[1]=0;attrs[2]=termios.CLOCAL|termios.CREAD|termios.CS8;attrs[3]=0
    attrs[4]=termios.B115200;attrs[5]=termios.B115200
    attrs[6][termios.VMIN]=0;attrs[6][termios.VTIME]=0
    termios.tcsetattr(fd,termios.TCSANOW,attrs)
    bits=array.array('i',[0]);fcntl.ioctl(fd,termios.TIOCMGET,bits,True)
    report(state='opening',initial_dtr=bool(bits[0]&termios.TIOCM_DTR),initial_rts=bool(bits[0]&termios.TIOCM_RTS))
    # Atomically deassert the pair; no reset pulse or sequential intermediate state.
    fcntl.ioctl(fd,termios.TIOCMBIC,array.array('i',[termios.TIOCM_DTR|termios.TIOCM_RTS]))
    report(state='capturing',commands_sent=0,baud=115200)
    end=time.monotonic()+3600;count=0
    while time.monotonic()<end and count<2*1024*1024:
        ready,_,_=select.select([fd],[],[],.5)
        if ready:
            data=os.read(fd,4096)
            if not data:break
            sys.stdout.buffer.write(data);sys.stdout.buffer.flush();count+=len(data)
    report(state='finished',bytes=count)
finally:
    os.close(fd)
