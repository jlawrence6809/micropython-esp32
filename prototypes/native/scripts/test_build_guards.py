#!/usr/bin/env python3
"""Syntax-only compiler checks for forbidden diagnostic combinations. No device I/O."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args()
entries=json.loads((a.build/'compile_commands.json').read_text())
source=Path(__file__).resolve().parents[1]/'main/main.c'
entry=next(e for e in entries if Path(e['file']).resolve()==source)
raw=entry.get('arguments') or shlex.split(entry['command'])
command=[];skip=False
for arg in raw:
    if skip:
        skip=False;continue
    if arg in ('-o','-MF','-MT','-MQ'):
        skip=True;continue
    if arg in ('-c','-MD','-MMD','-MP'):
        continue
    command.append(arg)
command.append('-fsyntax-only')
controller='GARDEN_CONTROLLER_IO'
faults=('BENCH_WATCHDOG_STALL','BENCH_IO_SELFTEST','BENCH_OTA_FAIL_PENDING_BOOT')
checks=[((),None)]
checks.extend(((controller,f),'Controller firmware cannot contain bench diagnostics') for f in faults)
checks.extend(((faults[i],faults[j]),'Select one bench diagnostic per build') for i in range(3) for j in range(i+1,3))
for flags,message in checks:
    result=subprocess.run(command+['-DCONFIG_'+f+'=1' for f in flags],cwd=entry['directory'],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if message is None:
        assert result.returncode==0, result.stderr
    else:
        assert result.returncode!=0 and message in result.stderr, result.stderr
print('Compiler guard PASS: normal syntax valid; all 6 controller/fault and overlapping-diagnostic combinations rejected; no device I/O')
