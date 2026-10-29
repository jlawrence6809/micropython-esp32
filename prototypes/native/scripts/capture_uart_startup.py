#!/usr/bin/env python3
"""Bounded private passive UART capture for an isolated attended controller.
No UART commands, resets, flash writes or GPIO arming. Opening/closing the
adapter can itself reset hardware; maintenance isolation is mandatory.
"""
import argparse
import datetime
import fcntl
import json
import os
import time
from pathlib import Path
import serial
from usb import prevent_linux_hangup_reset

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--directory',type=Path,required=True)
p.add_argument('--port',required=True)
p.add_argument('--maintenance-confirmed',action='store_true',required=True)
p.add_argument('--loads-disconnected',action='store_true',required=True)
p.add_argument('--seconds',type=int,default=600)
a=p.parse_args();os.umask(0o077);d=a.directory.resolve()
assert os.path.ismount('/var/lib/private-services') and d.is_relative_to('/var/lib/private-services')
assert 1<=a.seconds<=600
lock=(d.parent/'usb-maintenance.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
uid=int(os.environ.get('SUDO_UID',os.getuid()));gid=int(os.environ.get('SUDO_GID',os.getgid()))
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
base=d/('uart-startup-'+stamp)
log=base.with_suffix('.bin');status=base.with_suffix('.json')
state={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passive_only':True,
       'reset_issued':False,'commands_sent':0,'bytes':0,'state':'opening','pid':os.getpid(),'log':str(log)}
def save():
    tmp=status.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');os.chown(tmp,uid,gid);tmp.replace(status)
    pointer=d/'current-uart-capture';pointer.write_text(str(status)+'\n');os.chown(pointer,uid,gid)
save()
s=serial.Serial(port=None,baudrate=115200,timeout=.2);s.dtr=False;s.rts=False;s.port=a.port
try:
    with log.open('xb') as f:
        os.chown(log,uid,gid);s.open();prevent_linux_hangup_reset(s)
        state['state']='capturing';save();end=time.monotonic()+a.seconds
        while time.monotonic()<end and state['bytes']<2*1024*1024:
            data=s.read(4096)
            if data:
                f.write(data);f.flush();state['bytes']+=len(data);save()
        state['state']='finished';save()
except Exception as e:
    state.update(state='failed',error_type=type(e).__name__);save();raise
finally:
    s.close()
