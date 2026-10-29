#!/usr/bin/env python3
"""Explicit isolated-spare initial flash only. Streamed over SSH, never auto-run.
No profile/credentials/arm commands. One same-handle erase/write/verify/reset.
Caller creates an exclusive encrypted-vault journal before execution.
"""
import contextlib,hashlib,json,sys,time
from pathlib import Path

def run(config):
    if config.get('purpose')!='isolated-wifi-spare' or not all(config.get(k) is True for k in ['apply_confirmed','bare_usb_only_confirmed','backup_verified']):
        raise ValueError('Reviewed isolated-spare/verified-backup approval required')
    plan=config['plan'];expected=plan['expected_chip_mac']
    if expected in config['excluded_chip_macs'] or len(config['excluded_chip_macs'])<2:raise ValueError('Production target excluded')
    if plan['image']['contract']!='relay-profile1' or plan['gpio_to_remain_disarmed'] is not True:raise ValueError('Unarmed image required')
    if {f['offset'] for f in plan['files']}!={'0x0','0x8000','0xf000','0x20000'}:raise ValueError('Unexpected bootstrap offsets')
    args=[]
    for f in plan['files']:
        path=Path(config['artifact_directory'])/Path(f['file']).name
        if path.stat().st_size!=f['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Artifact changed')
        args += [f['offset'],str(path)]
    def emit(stage,**more):
        sys.__stdout__.write(json.dumps(dict(stage=stage,**more))+'\n');sys.__stdout__.flush()
    import esptool,termios
    esp=None
    with contextlib.redirect_stdout(sys.stderr):
        try:
            emit('identity_started');esp=esptool.detect_chip(port=config['port'],baud=115200)
            attrs=termios.tcgetattr(esp._port.fileno());attrs[2]&=~termios.HUPCL;termios.tcsetattr(esp._port.fileno(),termios.TCSANOW,attrs)
            if esp.CHIP_NAME!='ESP32-S3' or ':'.join(f'{x:02x}' for x in esp.read_mac())!=expected:raise ValueError('Wrong chip; no erase')
            si=esp.get_security_info()
            if si['parsed_flags']['SECURE_BOOT_EN'] or si['flash_crypt_cnt'].bit_count()%2:raise ValueError('Unsupported security; no erase')
            esp=esp.run_stub()
            if esptool.cmds.detect_flash_size(esp)!='16MB':raise ValueError('Wrong flash geometry; no erase')
            if esp.flash_md5sum(0,16777216)!=plan['original_device_md5']:raise ValueError('Flash changed since backup; no erase')
            emit('identity_backup_gate_verified')
            base=['--chip','esp32s3','--baud','115200','--no-stub','--after','no_reset_stub']
            for stage,extra in [('erase',['erase_flash']),('write',['write_flash','--flash_mode','dio','--flash_freq','80m','--flash_size','16MB']+args),('verify',['verify_flash','--diff','no']+args)]:
                emit(stage+'_started');esptool.main(base+extra,esp=esp);emit(stage+'_completed')
            emit('first_reset_started');esp.hard_reset();emit('first_reset_issued')
            esp._port.timeout=.25;boot=bytearray();deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                boot.extend(esp._port.read(4096))
                if len(boot)>262144:raise ValueError('Boot capture limit')
                if b'RUNTIME_READY ' in boot:break
            print('BOOT_CAPTURE_BEGIN\n'+boot.decode(errors='replace')+'\nBOOT_CAPTURE_END',flush=True)
            if b'BENCH_PASS ' not in boot or b'RUNTIME_READY ' not in boot or b' FAIL ' in boot:raise RuntimeError('Boot not confirmed; inspect, no reflash')
            emit('flash_verified_boot_observed',arming_issued=False,credentials_provisioned=False,serial_reopens=0)
        except BaseException as e:
            emit('stopped_inspect_no_replay',error_type=type(e).__name__);raise
        finally:
            if esp is not None:esp._port.close()
