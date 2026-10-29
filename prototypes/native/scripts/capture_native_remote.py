#!/usr/bin/env python3
"""Passive native USB capture, executed via SSH stdin; stdout ONLY to vault.
Caller supplies SETTINGS in stdin, holds maintenance lock and confirms isolation.
Opening/closing USB can itself restart the ESP32. No UART bytes/modem-line commands,
reset pulse, firmware/configuration write, GPIO commands or host service changes.
"""
import datetime
import fcntl
import json
import os
from pathlib import Path
import select
import sys
import termios
import time


def run(settings):
    assert settings['maintenance_confirmed'] is True and settings['ac_power_off_confirmed'] is True
    assert os.uname().nodename=='drallion'
    port=Path(settings['port']);tty=port.resolve();assert str(tty).startswith('/dev/ttyACM')
    parents=Path('/sys/class/tty/'+tty.name+'/device').resolve().parents
    usb=next(p for p in parents if (p/'idVendor').exists())
    assert (usb/'idVendor').read_text().strip()=='303a' and (usb/'idProduct').read_text().strip()=='1001'
    actual=(usb/'serial').read_text().strip().replace(':','').lower()
    assert actual==settings['expected_device_id']
    seconds=settings.get('seconds',15);assert 1<=seconds<=60
    def report(**data):
        print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),**data)),file=sys.stderr,flush=True)
    fd=os.open(port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd,termios.TIOCEXCL)
        attrs=termios.tcgetattr(fd);attrs[0]=0;attrs[1]=0
        attrs[2]=termios.CLOCAL|termios.CREAD|termios.CS8;attrs[3]=0
        attrs[4]=termios.B115200;attrs[5]=termios.B115200
        attrs[6][termios.VMIN]=0;attrs[6][termios.VTIME]=0
        termios.tcsetattr(fd,termios.TCSANOW,attrs)
        report(state='capturing',commands_sent=0,reset_command_issued=False,seconds=seconds)
        deadline=time.monotonic()+seconds;count=0
        while time.monotonic()<deadline and count<2*1024*1024:
            ready,_,_=select.select([fd],[],[],min(.5,max(0,deadline-time.monotonic())))
            if ready:
                data=os.read(fd,4096)
                if not data:break
                sys.stdout.buffer.write(data);sys.stdout.buffer.flush();count+=len(data)
        report(state='finished',bytes=count)
    finally:os.close(fd)
