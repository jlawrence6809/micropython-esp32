#!/usr/bin/env python3
"""Local bounded, HUP-independent receive-only boot supervisor; vault only.
Start with start_new_session=True. Public receive helper runs over SSH, raw UART
streams only to encrypted local files. No reset or other UART TX command.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--directory',type=Path,required=True)
p.add_argument('--flash-journal',type=Path,help='Optional verified initial-flash journal in vault; default uses historical flash-pass pointer')
a=p.parse_args();os.umask(0o077)
root=Path('/var/lib/private-services/agent-state/jeremy/garden-device-backups')
assert os.path.ismount('/var/lib/private-services') and a.directory.resolve().is_relative_to(root)
release=a.directory.resolve();plan=json.loads((release/'plan.local.json').read_text())
journal=a.flash_journal
if journal is None:
    flash=Path(json.loads((release/'flash-pass-current.local.json').read_text())['directory'])
    journal=flash/'execution.local.json'
assert journal.resolve().is_relative_to(root)
assert json.loads(journal.read_text())['state']=='flash_verified_waiting_operator_en'
with (root/'usb-maintenance.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    d=release/('boot-capture-'+stamp);d.mkdir(mode=0o700)
    state=dict(state='starting',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               pid=os.getpid(),uart_tx_bytes=0,reset_commands=0,seconds=360)
    status=d/'status.local.json'
    def save():
        status.write_text(json.dumps(state,indent=2)+'\n')
    save();(release/'boot-capture-current.local.json').write_text(json.dumps({'directory':str(d)},indent=2)+'\n')
    code=(Path(__file__).parent/'receive_relay_x8_boot.py').read_text()
    cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','drallion',
         'timeout --signal=INT --kill-after=10s 375s sudo -n /tmp/garden-barn-tools.kCNaHk/venv/bin/python -c '+
         shlex.quote(code)+' '+shlex.quote(plan['artifact_directory'])]
    c=dict(purpose='relay-x8-native-boot-capture',port=plan['port'],loads_disconnected=True,seconds=360)
    with (d/'uart.raw').open('xb') as out,(d/'stderr.log').open('xb') as err:
        try:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=out,stderr=err)
            state.update(state='ssh_running',ssh_pid=proc.pid);save()
            proc.communicate(json.dumps(c).encode(),timeout=395)
            state.update(state='completed' if proc.returncode==0 else 'failed',exit=proc.returncode)
        except BaseException as e:
            state.update(state='uncertain_inspect_no_replay',error_type=type(e).__name__);save();raise
        finally:
            b=(d/'uart.raw').read_bytes();state.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),
                    finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
