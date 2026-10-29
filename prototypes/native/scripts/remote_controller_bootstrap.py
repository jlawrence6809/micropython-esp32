#!/usr/bin/env python3
"""Attended isolated first bootstrap worker, passed via SSH stdin, never auto-run.
Public artifacts may be staged remotely. Profile/credentials only enter process
memory over stdin. Caller MUST create an exclusive private execution journal
before invoking run(); any uncertain execution requires inspection, NOT replay.
No GPIO arming, mutation retries, adapter reopen or automatic recovery path.
"""
import contextlib
import hashlib
import json
import sys
import time
from pathlib import Path


def run(config, Device):
    import esptool
    import termios
    if not all(config.get(k) is True for k in ('apply_confirmed','maintenance_confirmed','main_power_isolated','backup_verified')):
        raise ValueError('Explicit attended isolated bootstrap/verified backup required')
    plan=config['plan'];profile=config['profile'];expected=plan['expected_chip_mac'].replace(':','')
    if profile['hostname']!='barn' or len(profile['relays'])!=9 or profile['timezone'] is not None or profile['clock_source']!='manual' or profile['sensors_enabled'] is not False:
        raise ValueError('Reviewed Barn relay-only unconfirmed-clock profile required')
    if plan['image']['contract']!='relay-profile1' or plan['gpio_to_remain_disarmed'] is not True:
        raise ValueError('Unarmed controller contract required')
    if {x['offset'] for x in plan['files']}!={'0x0','0x8000','0xf000','0x20000'}:
        raise ValueError('Unexpected partition/bootstrap offsets')
    artifacts=[]
    for item in plan['files']:
        path=Path(config['artifact_directory'])/Path(item['file']).name
        if path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Staged artifact changed')
        artifacts.extend([item['offset'],str(path)])
    def emit(stage,**extra):
        sys.__stdout__.write(json.dumps({'stage':stage,**extra})+'\n');sys.__stdout__.flush()
    esp=None;dev=None
    with contextlib.redirect_stdout(sys.stderr):
        try:
            emit('identity_started')
            esp=esptool.detect_chip(port=config['port'],baud=115200)
            attrs=termios.tcgetattr(esp._port.fileno());attrs[2]&=~termios.HUPCL
            termios.tcsetattr(esp._port.fileno(),termios.TCSANOW,attrs)
            if esp.CHIP_NAME!='ESP32-S3' or ':'.join(f'{x:02x}' for x in esp.read_mac())!=plan['expected_chip_mac']:
                raise ValueError('Wrong chip; NO erase issued')
            si=esp.get_security_info()
            if si['parsed_flags']['SECURE_BOOT_EN'] or si['flash_crypt_cnt'].bit_count()%2:
                raise ValueError('Unsupported security state; NO erase issued')
            esp=esp.run_stub()
            if esptool.cmds.detect_flash_size(esp)!='16MB':raise ValueError('Wrong flash size; NO erase issued')
            emit('identity_verified')
            # External esptool instance keeps this SAME adapter open. --no-stub
            # suppresses redundant RAM uploads; esp is already a running stub.
            # no_reset_stub prevents app boot or stub->ROM transitions per stage.
            base=['--chip','esp32s3','--baud','115200','--no-stub','--after','no_reset_stub']
            for stage,args in [('erase',['erase_flash']),
                ('write',['write_flash','--flash_mode','dio','--flash_freq','80m','--flash_size','16MB']+artifacts),
                ('verify',['verify_flash','--diff','no']+artifacts)]:
                emit(stage+'_started')
                esptool.main(base+args,esp=esp)
                emit(stage+'_completed')
            emit('first_reset_started')
            esp.hard_reset();emit('first_reset_issued')
            # esptool may leave a blocking TTY timeout. Explicitly bound reads
            # before relying on a wall-clock loop deadline.
            esp._port.timeout=.25
            boot=bytearray();deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                boot.extend(esp._port.read(4096))
                if time.monotonic()>=deadline:break
                if len(boot)>262144:raise ValueError('Boot log bound exceeded')
                if b'RUNTIME_READY ' in boot:break
            print('BOOT_CAPTURE_BEGIN\n'+boot.decode('utf8',errors='replace')+'\nBOOT_CAPTURE_END',flush=True)
            if b'RUNTIME_READY ' not in boot or b'BENCH_PASS ' not in boot or b' FAIL ' in boot:
                raise RuntimeError('Native boot not confirmed; inspect, never reflash automatically')
            # Reuse the open maintenance TTY, avoiding an adapter reopen/reset.
            dev=Device.__new__(Device);dev.serial=esp._port;dev.serial.timeout=.25;dev.sequence=0
            dev.wait_healthy()
            def api(method,route,body=''):
                reply=dev.request(method,route,body)
                if reply['status']!=200:raise ValueError('API rejected; inspect without replay')
                return reply['data']
            routes=[('config','/api/config'),('io','/api/io/status'),('ota','/api/ota/status'),('watchdog','/api/watchdog/status'),('profile','/api/profile'),('wifi','/api/wifi/status')]
            def snapshot():
                s={key:api('GET',route) for key,route in routes}
                io,ota,cfg=s['io'],s['ota'],s['config']
                if not (io['device_id']==expected and ota['elf_sha256']==plan['image']['elf_sha256'] and cfg['device_role']=='relay-controller' and cfg['simulated'] is True and io['gpio_compiled'] is True and io['gpio_active'] is False and io['armed_for_saved_layout'] is False and io['cleanup_failed'] is False and ota['healthy'] is True and ota['running_state']=='valid' and ota['uploading'] is False and s['watchdog']['fault_injection'] is False and s['watchdog']['timeout_mask']==0):
                    raise ValueError('Controller identity/health/unarmed gate failed')
                return s
            def verify_profile(s):
                p=s['profile']
                if set(p)!=set(profile) or len(p['relays'])!=9:raise ValueError('Profile shape mismatch')
                for k,v in profile.items():
                    if k!='relays' and p[k]!=v:raise ValueError('Profile scalar mismatch')
                for actual,wanted in zip(p['relays'],profile['relays']):
                    if any(actual[k]!=v for k,v in wanted.items() if k!='value'):raise ValueError('Relay definition mismatch')
            before=snapshot();emit('native_before',snapshot=before)
            if before['wifi']['provisioned'] is not False:raise ValueError('Existing credentials; inspect, never replay')
            for row in profile['relays']:
                if api('POST','/api/validate-rule',row['rule'])['success'] is not True:raise ValueError('Lua validation failed')
            validation=api('POST','/api/profile/validate',json.dumps(profile))
            if validation['success'] is not True:raise ValueError('Profile validation failed')
            emit('profile_import_started')
            reply=api('POST','/api/profile/import',json.dumps(profile))
            if reply['success'] is not True or reply['outputs_applied'] is not True or reply.get('warning'):raise ValueError('Import uncertain/rejected; inspect')
            saved=snapshot();verify_profile(saved)
            if saved['io']['layout_hash']!=validation['layout_hash']:raise ValueError('Layout mismatch')
            emit('profile_import_acknowledged',snapshot=saved)
            emit('credential_provision_started')
            wifi=config['wifi'];reply=dev.command({'op':'provision','ssid':wifi['ssid'],'password':wifi['password']})
            if reply['status']!=200 or reply['data']['success'] is not True:raise ValueError('Credential completion unconfirmed; no replay')
            emit('credential_provision_acknowledged')
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                status=api('GET','/api/wifi/status')
                if status['provisioned'] and status['sta_connected']:break
                time.sleep(1)
            else:raise TimeoutError('Credentials acknowledged but Wi-Fi connection unconfirmed; inspect')
            after=snapshot();verify_profile(after)
            if after['ota']['boot_id']!=before['ota']['boot_id']:raise ValueError('Unexpected reset')
            emit('confirmed',snapshot=after,arming_issued=False,serial_reopens=0,
                 clock_confirmed=False,hostname_activation_pending=after['config']['restart_required'])
        except BaseException as error:
            emit('stopped_inspect_before_any_further_execution',error_type=type(error).__name__)
            raise
        finally:
            if dev is not None:dev.close()
            elif esp is not None:esp._port.close()
