#!/usr/bin/env python3
"""Attended first USB bootstrap, never OTA/arming. Verified backup + isolated board required.
Default prepares a frozen private plan. --apply executes ONCE; uncertainty stops.
"""
import argparse, datetime, fcntl, hashlib, json, os, re, shutil, subprocess, time
from pathlib import Path
from controller_release import image_info, require

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--directory',type=Path,required=True)
p.add_argument('--build',type=Path,default=Path('build-controller'))
p.add_argument('--port',required=True)
p.add_argument('--maintenance-confirmed',action='store_true',required=True)
p.add_argument('--loads-disconnected',action='store_true',required=True)
p.add_argument('--apply',action='store_true')
a=p.parse_args();os.umask(0o077);d=a.directory.resolve();build=a.build.resolve()
require(os.path.ismount('/var/lib/private-services') and d.is_relative_to('/var/lib/private-services'),'Vault required')
m=json.loads((d/'usb-backup-manifest.json').read_text());fs=json.loads((d/'filesystem-manifest.json').read_text())
require(m.get('verified') is True and fs.get('hostname_verified') is True and fs.get('relay_count')==8,'Verified Sunroom2 recovery material required')
original=d/'original-full-flash.bin'
require(original.stat().st_size==16*1024*1024 and hashlib.sha256(original.read_bytes()).hexdigest()==m['sha256'],'Original recovery image changed')
security=(d/'security-info.log').read_text()
require('Secure Boot: Disabled' in security and 'Flash Encryption: Disabled' in security,'Unsupported security state')
require(Path(a.port).resolve().is_char_device() and str(Path(a.port).resolve())==m['resolved_port'],'Serial endpoint changed')
planfile=d/'bootstrap-plan.json'
python='/home/jeremy/.espressif/python_env/idf5.5_py3.12_env/bin/python'
base=['sudo','-n',python,'-m','esptool','--chip','esp32s3','--port',a.port,'--baud','115200','--after','no_reset']
if not a.apply:
    require(not planfile.exists(),'Existing plan refused; inspect instead of replacing')
    cfg=(build/'sdkconfig').read_text()
    require('CONFIG_GARDEN_CONTROLLER_IO=y' in cfg and 'CONFIG_ESP_CONSOLE_UART_DEFAULT=y' in cfg,'Controller UART build required')
    require(not any(x.startswith('CONFIG_BENCH') and x.endswith('=y') for x in cfg.splitlines()),'Diagnostic build forbidden')
    args=json.loads((build/'flasher_args.json').read_text())
    require(args['flash_settings']=={'flash_mode':'dio','flash_size':'16MB','flash_freq':'80m'},'Unexpected flash settings')
    require(set(args['flash_files'])=={'0x0','0x8000','0xf000','0x20000'},'Unexpected bootstrap layout')
    info=image_info((build/'garden_native_probe.bin').read_bytes())
    release=d/'native-release';release.mkdir(mode=0o700)
    frozen=[]
    for off,name in sorted(args['flash_files'].items(),key=lambda x:int(x[0],0)):
        src=(build/name).resolve();require(src.is_relative_to(build) and src.is_file(),'Unsafe artifact path')
        dest=release/src.name;shutil.copyfile(src,dest);dest.chmod(0o400)
        frozen.append({'offset':off,'file':str(dest),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    shutil.copyfile(build/'sdkconfig',release/'sdkconfig')
    plan={'image':info,'files':frozen,'original_sha256':m['sha256'],'expected_chip_mac':m['expected_chip_mac'],'gpio_to_remain_disarmed':True,'clock_confirmed':False,'flash_settings':args['write_flash_args'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with planfile.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
    recovery=['# Private recovery procedure: review exact chip/port and disconnect all loads first.',
              '# No recovery command has been executed. Verify original SHA256 before use.',
              '# Full backup includes original bootloader, partition table, NVS and filesystem.',
              '# Do not unplug/swap the board during backup/bootstrap/recovery.',
              f'Original SHA256: {m["sha256"]}',
              'Use the same esptool 4.12.0 / 115200 baud / esp32s3 / recorded USB endpoint.',
              'Explicit recovery sequence: identify exact chip; erase_flash; write_flash 0 original-full-flash.bin',
              'with flash_mode/freq/size keep; verify_flash 0 original-full-flash.bin; then explicit hard reset.',
              'Never automatically restore after an uncertain operation or reconnect connected loads.']
    (d/'RECOVERY.private.txt').write_text('\n'.join(recovery)+'\n')
    print('Frozen controller bootstrap/recovery plan prepared. NO device write or arming issued.');raise SystemExit(0)
plan=json.loads(planfile.read_text())
require(plan['expected_chip_mac']==m['expected_chip_mac'] and plan['original_sha256']==m['sha256'] and plan['gpio_to_remain_disarmed'] is True,'Plan identity mismatch')
for item in plan['files']:
    f=Path(item['file']);require(f.resolve().is_relative_to(d/'native-release') and f.stat().st_size==item['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256'],'Frozen artifact changed')
lock=(d.parent/'usb-maintenance.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
jp=d/'bootstrap-journal.json';require(not jp.exists(),'Existing execution journal refused; inspect actual device before any retry')
journal={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'steps':[],'arming_issued':False}
def save():
    tmp=jp.with_suffix('.tmp');tmp.write_text(json.dumps(journal,indent=2)+'\n');tmp.replace(jp)
def run(name,args,timeout=90):
    step={'name':name,'state':'started'};journal['steps'].append(step);save();t=time.monotonic()
    with (d/(name+'.log')).open('x') as f:r=subprocess.run(base+args,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    step.update(state='complete' if r.returncode==0 else 'failed',exit=r.returncode,seconds=round(time.monotonic()-t,2));save()
    require(r.returncode==0,'Operation failed/uncertain; inspect private log and actual device. No automatic retry.')
    text=(d/(name+'.log')).read_text();mac=re.search(r'MAC: ([0-9a-f:]+)',text,re.I)
    require(mac is not None and mac.group(1).lower()==m['expected_chip_mac'],'Unexpected chip identity; stop')
    return text
identity=run('bootstrap-identity',['flash_id'],45)
require('Detected flash size: 16MB' in identity,'Flash geometry changed')
run('bootstrap-erase',['erase_flash'],240)
files=[]
for item in plan['files']:files.extend([item['offset'],item['file']])
run('bootstrap-write',['write_flash']+plan['flash_settings']+files,420)
run('bootstrap-verify',['verify_flash','--diff','no']+files,180)
# read_mac first verifies connected identity; --after hard_reset starts the new app.
oldbase=base.copy();base[base.index('no_reset')]='hard_reset'
run('bootstrap-reset',['read_mac'],45)
journal.update(flash_verified=True,reset_issued=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
print('Controller image flashed and verified; explicit first reset issued. No GPIO arm command. Inspect boot before provisioning.')
