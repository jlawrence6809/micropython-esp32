#!/usr/bin/env python3
"""Verify one post-validation task stall on the memory-only spare, then restore normal."""
import argparse
import copy
from pathlib import Path
from ota import Bench, update, image_elf_hash

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('host')
p.add_argument('diagnostic',type=Path)
p.add_argument('--normal',type=Path,default=Path('build/garden_native_probe.bin'))
p.add_argument('--task',type=int,choices=range(4),default=0)
a=p.parse_args()
b=Bench(a.host)
normal,diagnostic=a.normal.read_bytes(),a.diagnostic.read_bytes()
normal_sha,diagnostic_sha=image_elf_hash(normal),image_elf_hash(diagnostic)
assert normal_sha!=diagnostic_sha
before=b.wait(lambda s:s['healthy'] and s['running_state']=='valid')
assert before['elf_sha256']==normal_sha
assert b.get('/api/watchdog/status')['fault_injection'] is False
assert b.get('/api/io/status')['gpio_compiled'] is False
original=b.get('/api/profile')

def static_profile(value):
    result=copy.deepcopy(value)
    for row in result['relays']:
        row.pop('value',None);row.pop('auto',None)
    return result

try:
    started=update(b,diagnostic)
    status=b.get('/api/watchdog/status')
    assert status['monitor_active'] and status['fault_injection'] and status['fault_task']==a.task
    assert b.get('/api/io/status')['gpio_compiled'] is False
    # Unlike a pending-boot failure, this image first became valid and then reset
    # to ITSELF. No rollback to an older configuration-unaware image is attempted.
    after=b.wait(lambda s:s['healthy'] and s['running_state']=='valid' and
                 s['elf_sha256']==diagnostic_sha and s['boot_id']!=started['boot_id'])
    assert after['running_slot']==started['running_slot']
    assert after['previous_watchdog_mask']==1<<a.task
    assert b.get('/api/watchdog/status')['previous_watchdog_mask']==1<<a.task
    assert static_profile(b.get('/api/profile'))==static_profile(original)
    print('Runtime watchdog PASS: stalled task',a.task,'reset the already-valid image; correct mask; profile preserved')
finally:
    current=b.wait(lambda s:s['healthy'] and s['running_state']=='valid')
    if current['elf_sha256']==diagnostic_sha:
        update(b,normal)
    elif current['elf_sha256']!=normal_sha:
        raise RuntimeError('Unexpected spare firmware; inspect before further writes')
    assert b.get('/api/watchdog/status')['fault_injection'] is False
    assert b.get('/api/watchdog/status')['monitor_active'] is True
    assert b.get('/api/io/status')['gpio_compiled'] is False
    assert static_profile(b.get('/api/profile'))==static_profile(original)
    print('FINAL: verified normal memory-only image restored; continuous watchdog active; fault disabled')
