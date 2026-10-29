#!/usr/bin/env python3
"""Isolated Barn startup/restore after verified flash; NO flash writes or arming.
Caller creates NEW exclusive vault journal before execution via SSH stdin.
Uses one supported S3 watchdog reset, then reads actual state before any setup.
Only exact factory -> reviewed profile or already-restored profile is accepted.
Credentials are sent only if fresh device state says unprovisioned. No retries.
"""
import contextlib
import hashlib
import json
import sys
import time


def comparable(profile):
    result=json.loads(json.dumps(profile))
    for row in result['relays']:row.pop('value',None)
    return result


def factory_profile():
    return dict(format_version=1,hostname='garden-bench',timezone=None,clock_source='manual',
        schedule_policy='edge_no_catchup',sensors_enabled=False,
        sensor_pins={k:-1 for k in ('i2c_scl','i2c_sda','ds18b20','photo_sensor','light_switch','reset_switch')},
        relays=[dict(pin=1,label='SIMULATED relay',rule='return nil',value=False,auto=False,
                     isInverted=False,defaultValue=False,defaultAuto=False)])


def restore(dev,config,emit):
    plan=config['plan'];wanted=config['profile'];wifi=config['wifi']
    def api(method,route,body=''):
        r=dev.request(method,route,body)
        if r['status']!=200:raise ValueError('API rejected; inspect without replay')
        return r['data']
    routes=[('config','/api/config'),('io','/api/io/status'),('ota','/api/ota/status'),('watchdog','/api/watchdog/status'),('profile','/api/profile'),('wifi','/api/wifi/status')]
    def snapshot():
        s={k:api('GET',route) for k,route in routes};io,ota,cfg=s['io'],s['ota'],s['config']
        if not (io['device_id']==plan['expected_chip_mac'].replace(':','') and ota['elf_sha256']==plan['image']['elf_sha256'] and cfg['device_role']=='relay-controller' and cfg['simulated'] is True and io['gpio_compiled'] is True and io['gpio_active'] is False and io['armed_for_saved_layout'] is False and io['cleanup_failed'] is False and ota['healthy'] is True and ota['running_state']=='valid' and ota['uploading'] is False and ota['running_slot']=='ota_0' and ota['boot_slot']=='ota_0' and s['watchdog']['fault_injection'] is False and s['watchdog']['timeout_mask']==0):raise ValueError('Identity/health/unarmed gate failed')
        return s
    dev.wait_healthy();before=snapshot();emit('native_before',snapshot=before)
    if wanted['hostname']!='barn' or len(wanted['relays'])!=9 or wanted['timezone'] is not None or wanted['clock_source']!='manual' or wanted['sensors_enabled'] is not False:raise ValueError('Unexpected intended Barn profile')
    actual=comparable(before['profile']);desired=comparable(wanted)
    if actual==desired:
        emit('profile_already_restored_no_mutation')
    elif actual==comparable(factory_profile()):
        if before['wifi']['provisioned'] is not False:raise ValueError('Factory profile with existing credentials requires review')
        for row in wanted['relays']:
            if api('POST','/api/validate-rule',row['rule'])['success'] is not True:raise ValueError('Lua validation failed')
        valid=api('POST','/api/profile/validate',json.dumps(wanted))
        if valid['success'] is not True:raise ValueError('Profile validation failed')
        if api('GET','/api/ota/status')['boot_id']!=before['ota']['boot_id']:raise ValueError('Boot changed before restore')
        emit('profile_import_started')
        reply=api('POST','/api/profile/import',json.dumps(wanted))
        if reply['success'] is not True or reply['outputs_applied'] is not True or reply.get('warning'):raise ValueError('Profile completion unconfirmed; do not replay')
        saved=snapshot()
        if comparable(saved['profile'])!=desired or saved['io']['layout_hash']!=valid['layout_hash']:raise ValueError('Profile/layout read-back mismatch')
        emit('profile_import_acknowledged',snapshot=saved)
    else:raise ValueError('Nonfactory unexpected profile; no overwrite permitted')
    current=snapshot()
    if current['ota']['boot_id']!=before['ota']['boot_id']:raise ValueError('Boot changed; inspect without replay')
    if current['wifi']['provisioned'] is False:
        emit('credential_provision_started')
        reply=dev.command({'op':'provision','ssid':wifi['ssid'],'password':wifi['password']})
        if reply['status']!=200 or reply['data']['success'] is not True:raise ValueError('Credentials uncertain; do not replay')
        emit('credential_provision_acknowledged')
    elif current['wifi'].get('sta_ssid')==wifi['ssid']:emit('credentials_already_present_no_mutation')
    else:raise ValueError('Existing Wi-Fi differs; no overwrite permitted')
    end=time.monotonic()+60
    while time.monotonic()<end:
        status=api('GET','/api/wifi/status')
        if status['provisioned'] and status['sta_connected']:break
        time.sleep(1)
    else:raise TimeoutError('Credential state confirmed but connection unconfirmed; inspect, no replay')
    after=snapshot()
    if comparable(after['profile'])!=desired or after['ota']['boot_id']!=before['ota']['boot_id']:raise ValueError('Final profile/boot mismatch')
    emit('confirmed',snapshot=after,arming_issued=False,serial_reopens=0,clock_confirmed=False,
         hostname_activation_pending=after['config']['restart_required'])


def run(config,Device,prevent_linux_hangup_reset):
    import esptool
    if not all(config.get(k) is True for k in ('maintenance_confirmed','main_power_isolated','backup_verified','apply_confirmed')):raise ValueError('Explicit isolated maintenance and verified recovery required')
    def emit(stage,**extra):
        sys.__stdout__.write(json.dumps({'stage':stage,**extra})+'\n');sys.__stdout__.flush()
    esp=None;dev=None
    with contextlib.redirect_stdout(sys.stderr):
        try:
            # Use esptool's standard ROM-entry handshake. A no-reset serial
            # open did not synchronize this adapter; no watchdog reset/setup
            # occurred in that failed connection attempt.
            emit('rom_connection_started')
            esp=esptool.detect_chip(port=config['port'],baud=115200,connect_mode='default_reset')
            prevent_linux_hangup_reset(esp._port)
            if esp.CHIP_NAME!='ESP32-S3' or ':'.join(f'{b:02x}' for b in esp.read_mac())!=config['plan']['expected_chip_mac']:raise ValueError('Wrong chip; stop')
            security=esp.get_security_info()
            if security['parsed_flags']['SECURE_BOOT_EN'] or security['flash_crypt_cnt'].bit_count()%2:raise ValueError('Unsupported security state')
            esp=esp.run_stub()
            if esptool.cmds.detect_flash_size(esp)!='16MB':raise ValueError('Wrong geometry')
            for item in config['plan']['files']:
                expected=hashlib.md5(bytes.fromhex(config['artifact_hex'][item['offset']])).hexdigest()
                matches=esp.flash_md5sum(int(item['offset'],0),item['bytes'])==expected
                # OTA selection data is mutable on first boot/health validation;
                # comparing it to the erased bootstrap template is invalid.
                # Native snapshot MUST subsequently confirm valid ota_0 selection.
                emit('installed_digest_checked',offset=item['offset'],matches_bootstrap=matches,mutable=item['offset']=='0xf000')
                if not matches and item['offset']!='0xf000':raise ValueError('Immutable installed image differs; NO automatic reflash')
            emit('installed_bootloader_partition_application_reverified')
            esp._port.dtr=False;esp._port.rts=False
            emit('software_watchdog_reset_started')
            esp.watchdog_reset();esp._port.timeout=.25
            emit('software_watchdog_reset_issued')
            boot=bytearray();end=time.monotonic()+40
            while time.monotonic()<end:
                boot.extend(esp._port.read(4096))
                if time.monotonic()>=end:break
                if len(boot)>262144:raise ValueError('Boot capture bound exceeded')
                if b'RUNTIME_READY ' in boot:break
            print('BOOT_CAPTURE_BEGIN\n'+boot.decode('utf8',errors='replace')+'\nBOOT_CAPTURE_END',flush=True)
            emit('boot_observation',runtime_ready=b'RUNTIME_READY ' in boot,rom_download=b'waiting for download' in boot)
            if b'RUNTIME_READY ' not in boot or b'BENCH_PASS ' not in boot or b' FAIL ' in boot:raise RuntimeError('Native boot not confirmed; stop without further resets')
            dev=Device.__new__(Device);dev.serial=esp._port;dev.serial.timeout=.25;dev.sequence=0
            restore(dev,config,emit)
        except BaseException as error:
            emit('stopped_inspect_before_further_execution',error_type=type(error).__name__)
            raise
        finally:
            if dev is not None:dev.close()
            elif esp is not None:esp._port.close()
