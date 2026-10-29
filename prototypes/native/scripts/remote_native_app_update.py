#!/usr/bin/env python3
"""One-shot isolated Barn native-USB app replacement. No full erase/NVS/arming.
Caller must create exclusive private journal first; public staged app only.
Old immutable artifacts reverified before a single write at ota_0 (0x20000).
Intended solely for this verified factory/unarmed initial commissioning state,
NOT routine updates on deployed/armed controllers. No retries or fallback.
"""
import contextlib
import hashlib
import json
from pathlib import Path
import sys


def run(config,prevent_linux_hangup_reset):
    import esptool
    if not all(config.get(k) is True for k in ('apply_confirmed','maintenance_confirmed','main_power_isolated','factory_unarmed_boot_observed','full_backup_verified')):raise ValueError('Explicit isolated factory-state maintenance required')
    app=Path(config['app_path']);data=app.read_bytes()
    if len(data)!=config['new_image']['bytes'] or len(data)>0x300000 or hashlib.sha256(data).hexdigest()!=config['new_image']['image_sha256']:raise ValueError('Staged image changed')
    if config['new_image']['contract']!='relay-profile1':raise ValueError('Controller contract required')
    def emit(stage,**extra):
        sys.__stdout__.write(json.dumps({'stage':stage,**extra})+'\n');sys.__stdout__.flush()
    esp=None
    with contextlib.redirect_stdout(sys.stderr):
        try:
            emit('identity_started')
            esp=esptool.detect_chip(port=config['port'],baud=115200)
            prevent_linux_hangup_reset(esp._port)
            if esp.CHIP_NAME!='ESP32-S3' or ':'.join(f'{x:02x}' for x in esp.read_mac())!=config['expected_chip_mac']:raise ValueError('Wrong chip')
            si=esp.get_security_info()
            if si['parsed_flags']['SECURE_BOOT_EN'] or si['flash_crypt_cnt'].bit_count()%2:raise ValueError('Unsupported security state')
            esp=esp.run_stub()
            if esptool.cmds.detect_flash_size(esp)!='16MB':raise ValueError('Wrong flash geometry')
            for item in config['old_immutable']:
                if esp.flash_md5sum(int(item['offset'],0),item['bytes'])!=item['md5']:raise ValueError('Current immutable image differs; NO write issued')
            emit('old_bootloader_partition_app_verified')
            base=['--chip','esp32s3','--baud','115200','--no-stub','--after','no_reset_stub']
            emit('app_write_started',offset='0x20000',full_erase=False,nvs_write=False)
            esptool.main(base+['write_flash','--flash_mode','dio','--flash_freq','80m','--flash_size','16MB','0x20000',str(app)],esp=esp)
            emit('app_write_completed')
            esptool.main(base+['verify_flash','--diff','no','0x20000',str(app)],esp=esp)
            if esp.flash_md5sum(0x20000,len(data))!=hashlib.md5(data).hexdigest():raise ValueError('Final application digest mismatch')
            emit('app_verified')
            emit('native_reset_started');esp.hard_reset();emit('native_reset_issued')
            # Native USB can re-enumerate on reset. Do not use a stale descriptor
            # or implicitly reopen. Caller separately inspects new device state.
            emit('flash_complete_inspect_boot_separately',arming_issued=False)
        except BaseException as error:
            emit('stopped_inspect_before_any_further_execution',error_type=type(error).__name__)
            raise
        finally:
            if esp is not None:esp._port.close()
