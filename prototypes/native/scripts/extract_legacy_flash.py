#!/usr/bin/env python3
"""Recover a VERIFIED MicroPython LittleFS dump offline; no serial/device writes.
Run with littlefs-python in an ephemeral environment. Never auto-format a failed mount.
"""
import argparse, hashlib, json, os, struct
from pathlib import Path, PurePosixPath
from littlefs import LittleFS, UserContext
from prepare_migration import translate

p=argparse.ArgumentParser();p.add_argument('directory',type=Path)
p.add_argument('--expected-hostname',choices=('sunroom2','barn'),default='sunroom2')
a=p.parse_args();os.umask(0o077)
expected_count={'sunroom2':8,'barn':9}[a.expected_hostname]
d=a.directory.resolve()
if not os.path.ismount('/var/lib/private-services') or not d.is_relative_to('/var/lib/private-services'):raise SystemExit('Vault required')
m=json.loads((d/'usb-backup-manifest.json').read_text())
if m.get('verified') is not True:raise SystemExit('Verified full-flash backup required')
image=(d/'original-full-flash.bin').read_bytes()
if len(image)!=16*1024*1024 or hashlib.sha256(image).hexdigest()!=m['sha256']:raise SystemExit('Backup integrity failure')
parts=[]
for at in range(0x8000,0x8c00,32):
    block=image[at:at+32]
    if block[:2]==b'\xff\xff':break
    if block[:2]==b'\xeb\xeb':
        if hashlib.md5(image[0x8000:at]).digest()!=block[16:32]:raise SystemExit('Partition checksum mismatch')
        break
    magic,typ,sub,offset,size,label,flags=struct.unpack('<HBBII16sI',block)
    if magic!=0x50aa or offset+size>len(image):raise SystemExit('Unexpected partition table')
    parts.append(dict(type=typ,subtype=sub,offset=offset,size=size,label=label.rstrip(b'\0').decode(),flags=flags))
vfs=[x for x in parts if x['type']==1 and x['label']=='vfs']
if len(vfs)!=1:raise SystemExit('Expected one legacy VFS partition')
vfs=vfs[0]
class ReadOnly(UserContext):
    def prog(self,*args):return -5
    def erase(self,*args):return -5
ctx=ReadOnly(buffer=bytearray(image[vfs['offset']:vfs['offset']+vfs['size']]))
fs=LittleFS(context=ctx,mount=False,block_size=4096,block_count=vfs['size']//4096,read_size=32,prog_size=256,cache_size=256,lookahead_size=32)
fs.mount()  # Explicit mount; never LittleFS's automatic format fallback.
out=d/'legacy-filesystem';out.mkdir(mode=0o700)
checks={};total=0
for folder,dirs,files in fs.walk('/'):
    for name in files:
        rel=PurePosixPath(folder.lstrip('/'))/name
        if rel.is_absolute() or '..' in rel.parts:raise SystemExit('Unsafe filesystem name')
        with fs.open('/'+str(rel),'rb') as f:data=f.read()
        total+=len(data)
        if total>vfs['size'] or len(checks)>4096:raise SystemExit('Filesystem bounds exceeded')
        dest=out/str(rel);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(data)
        checks[str(rel)]=hashlib.sha256(data).hexdigest()
fs.unmount()
cfg=json.loads((out/'config.json').read_text());legacy=json.loads((out/'relays.json').read_text())['relays']
if cfg.get('hostname','').lower()!=a.expected_hostname or len(legacy)!=expected_count:raise SystemExit('Wrong application identity/relay count; stop before flashing')
if not cfg.get('wifi',{}).get('ssid') or not isinstance(cfg['wifi'].get('password'),str):raise SystemExit('Wi-Fi material missing; inspect privately')
relays=[]
for r in legacy:
    lua,_=translate(r.get('rule',''))
    row={key:r[key] for key in ('pin','label','isInverted','defaultValue','defaultAuto')}
    row.update(rule=lua,value=r['defaultValue'],auto=r['defaultAuto']);relays.append(row)
profile=dict(format_version=1,hostname=a.expected_hostname,relays=relays,
             sensor_pins=cfg['sensor_pins'],timezone=None,clock_source='manual',
             schedule_policy='edge_no_catchup',sensors_enabled=False)
with (d/'native-profile.unconfirmed.local.json').open('x') as f:json.dump(profile,f,indent=2);f.write('\n')
record={'partitions':parts,'files':checks,'file_count':len(checks),'bytes':total,'hostname_verified':True,'hostname':a.expected_hostname,'relay_count':len(relays),'wifi_recovered':True,'clock_policy_confirmed':False,'gpio_activation_authorized':False}
with (d/'filesystem-manifest.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(f'Offline LittleFS recovered; {a.expected_hostname} identity and {expected_count} relays confirmed; Wi-Fi retained privately. Clock unconfirmed, GPIO activation not authorized.')
