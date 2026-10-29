#!/usr/bin/env python3
"""Attended, read-only ESP32-S3 full-flash backup. Opens/reset USB; never writes flash."""
import argparse, datetime, fcntl, hashlib, json, os, re, subprocess, time
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--port',required=True)
p.add_argument('--directory',type=Path,required=True)
p.add_argument('--maintenance-confirmed',action='store_true',required=True)
a=p.parse_args();os.umask(0o077)
if not os.path.ismount('/var/lib/private-services'):raise SystemExit('Private vault required')
d=a.directory.resolve()
if not d.is_relative_to('/var/lib/private-services') or not d.is_dir():raise SystemExit('Existing vault directory required')
if not Path(a.port).resolve().is_char_device():raise SystemExit('Serial device missing')
initial=(d/'flash-id.log').read_text()
mac=re.search(r'MAC: ([0-9a-f:]+)',initial,re.I)
if not mac or 'ESP32-S3' not in initial or 'Detected flash size: 16MB' not in initial:raise SystemExit('Expected S3/16MB identification missing')
expected=mac.group(1).lower()
lock=(d.parent/'usb-maintenance.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
python='/home/jeremy/.espressif/python_env/idf5.5_py3.12_env/bin/python'
base=['sudo','-n',python,'-m','esptool','--port',a.port,'--baud','460800','--after','no_reset']
manifest={'format':1,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'port':a.port,'resolved_port':str(Path(a.port).resolve()),'expected_chip_mac':expected,'flash_bytes':16*1024*1024,'writes_issued':False,'steps':[]}
mp=d/'usb-backup-manifest.json'
if mp.exists():raise SystemExit('Existing backup journal refused; inspect before any retry')
def journal():
    tmp=mp.with_suffix('.tmp');tmp.write_text(json.dumps(manifest,indent=2)+'\n');tmp.replace(mp)
def run(name,args,timeout):
    step={'name':name,'state':'started'};manifest['steps'].append(step);journal();t=time.monotonic()
    with (d/(name+'.log')).open('x') as log:
        r=subprocess.run(base+args,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    step.update(state='complete' if r.returncode==0 else 'failed',exit=r.returncode,seconds=round(time.monotonic()-t,2));journal()
    if r.returncode:raise SystemExit('Read-only step failed; inspect private journal/log. No automatic retry.')
    text=(d/(name+'.log')).read_text()
    observed=re.search(r'MAC: ([0-9a-f:]+)',text,re.I)
    if observed and observed.group(1).lower()!=expected:raise SystemExit('Chip changed; stop')
run('security-info',['get_security_info'],45)
image=d/'original-full-flash.bin'
with image.open('xb'):pass  # Owner-only, caller-owned file before privileged tool opens it.
run('read-full-flash',['read_flash','--no-progress','0','0x1000000',str(image)],1100)
if image.stat().st_size!=manifest['flash_bytes']:raise SystemExit('Incomplete dump; not a recovery image')
with image.open('rb') as f:manifest['sha256']=hashlib.file_digest(f,'sha256').hexdigest()
journal()
# Independent on-device readback digest comparison, not a second host-file hash.
run('verify-full-flash',['verify_flash','--diff','no','0',str(image)],300)
manifest.update(verified=True,verification='esptool full-range device-flash digest matched host image',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());journal()
print('Full 16MiB backup and independent device-digest verification complete; original remains in bootloader. No flash writes issued.')
