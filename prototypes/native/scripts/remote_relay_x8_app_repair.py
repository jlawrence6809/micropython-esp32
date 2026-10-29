#!/usr/bin/env python3
"""Original-ESP32 failed-first-boot app repair ONLY; fresh private journal required.
No whole-chip erase, NVS/OTAdata writes, reset, credentials or GPIO activation.
Exact previous app/boot/table and blank inactive slot required. NVS must be blank,
or separately preserved/fenced AND independently decoded as strict schema-only.
"""
import contextlib
import hashlib
import json
import re
import sys
from pathlib import Path
from remote_relay_x8_bootstrap import guard_port, require
from controller_release import image_info


def validate(c):
    require(c.get('purpose') == 'relay-x8-failed-first-boot-app-repair', 'Wrong purpose')
    require(all(c.get(k) is True for k in ['apply_confirmed','loads_disconnected','backup_verified','remain_unarmed']), 'Unloaded/backup/unarmed gates required')
    require(re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', c['expected_chip_mac']), 'Bad identity')
    require(c['expected_chip_revision'] == 301 and c['app_offset'] == 0x20000 and c['slot_bytes'] == 0x180000, 'Wrong target/layout')
    f=c['image']; require(f['file']=='garden_native_probe.bin', 'Wrong filename')
    path=Path(c['artifact_directory'])/f['file'];require(not path.is_symlink(), 'Artifact symlink')
    b=path.read_bytes();require(image_info(b,'esp32') == f['audit'], 'Image audit/hash mismatch')
    require(f['audit']['elf_sha256'] != c['previous_image']['elf_sha256'], 'Same image; no repair')
    require(c['previous_image']['chip_target']=='esp32' and c['previous_image']['contract']=='relay-profile1' and
            288<=c['previous_image']['bytes']<=c['slot_bytes'], 'Previous image metadata mismatch')
    expected={'bootloader':0x1000,'partition_table':0x8000,'previous_app':0x20000}
    require(len(c['current_ranges'])==3 and {x['name'] for x in c['current_ranges']}==set(expected), 'Current artifact ranges required')
    limits={'bootloader':0x7000,'partition_table':0x1000,'previous_app':0x180000}
    for x in c['current_ranges']:
        require(x['offset']==expected[x['name']] and 0<x['bytes']<=limits[x['name']] and
                re.fullmatch(r'[0-9a-f]{32}',x['md5']), 'Malformed current digest range')
    require(next(x for x in c['current_ranges'] if x['name']=='previous_app')['bytes']==c['previous_image']['bytes'], 'Previous app length mismatch')
    if 'inert_nvs' in c:
        review=c['inert_nvs']
        require(review.get('kind')=='schema_only' and review.get('bytes')==0x6000 and
                review.get('activation_profile_credentials_absent') is True and
                re.fullmatch(r'[0-9a-f]{32}',review.get('md5','')) and
                re.fullmatch(r'[0-9a-f]{64}',review.get('sha256','')), 'Malformed inert-NVS review')
    return path,b


def run(c):
    path,b=validate(c)
    import esptool
    import serial
    import termios
    def emit(stage,**more):
        sys.__stdout__.write(json.dumps(dict(stage=stage,**more))+'\n');sys.__stdout__.flush()
    with guard_port(c),contextlib.redirect_stdout(sys.stderr):
        port=serial.Serial(port=None,baudrate=115200,timeout=.25,write_timeout=8,exclusive=True)
        port.dtr=False;port.rts=False;port.port=c['port']
        try:
            emit('serial_open_started');port.open()
            a=termios.tcgetattr(port.fileno());a[2]&=~termios.HUPCL;termios.tcsetattr(port.fileno(),termios.TCSANOW,a)
            e=esptool.ESP32ROM(port,baud=115200);e.connect(mode='no_reset',attempts=1)
            require(e.CHIP_NAME=='ESP32' and ':'.join(f'{x:02x}' for x in e.read_mac())==c['expected_chip_mac'] and
                    e.get_chip_revision()==301,'Wrong chip; no write')
            require(not e.secure_download_mode and not e.get_secure_boot_enabled() and
                    not e.get_flash_encryption_enabled() and not e.get_encrypted_download_disabled(),'Unsupported security; no write')
            e=e.run_stub();e.WRITE_FLASH_ATTEMPTS=1;esptool.loader.WRITE_BLOCK_ATTEMPTS=1
            require(esptool.cmds.detect_flash_size(e)=='4MB','Wrong geometry; no write')
            for x in c['current_ranges']:
                require(e.flash_md5sum(x['offset'],x['bytes'])==x['md5'],'Current artifact changed; no write')
            unchanged=[(0x9000,0x6000),(0x1a0000,0x180000),(0xf000,0x2000)]
            before=[e.flash_md5sum(off,n) for off,n in unchanged]
            if 'inert_nvs' in c:
                from relay_x8_inert_nvs import inspect
                actual=inspect(e.read_flash(0x9000,0x6000))
                require(actual==c['inert_nvs'] and actual['md5']==before[0], 'NVS review/fence changed; no write')
                emit('strict_schema_only_nvs_verified')
            else:
                require(before[0]==hashlib.md5(b'\xff'*0x6000).hexdigest(),'NVS no longer blank; no write')
            require(before[1]==hashlib.md5(b'\xff'*0x180000).hexdigest(),'Inactive slot not blank; no write')
            emit('identity_security_geometry_previous_artifacts_unarmed_verified',ota_data_md5=before[2])
            base=['--chip','esp32','--baud','115200','--before','no_reset','--no-stub','--after','no_reset_stub']
            args=['0x20000',str(path)]
            emit('app_write_started')
            esptool.main(base+['write_flash','--flash_mode','dio','--flash_freq','40m','--flash_size','4MB']+args,esp=e)
            emit('app_write_completed');emit('app_verify_started')
            esptool.main(base+['verify_flash','--diff','no']+args,esp=e)
            require(e.flash_md5sum(0x20000,len(b))==hashlib.md5(b).hexdigest(),'New app read-back mismatch')
            for x in c['current_ranges']:
                if x['name']!='previous_app':require(e.flash_md5sum(x['offset'],x['bytes'])==x['md5'],'Boot/table changed')
            require([e.flash_md5sum(off,n) for off,n in unchanged]==before,'NVS/inactive slot/OTAdata changed')
            emit('flash_verified_waiting_operator_en',app_bytes=len(b),erase_all_commands=0,reset_commands=0,
                 arming_issued=False,provision_issued=False,other_regions_unchanged=True)
        except BaseException as ex:
            emit('stopped_inspect_no_replay',error_type=type(ex).__name__);raise
        finally:
            port.close();emit('serial_closed')


if __name__=='__main__':run(json.load(sys.stdin))
