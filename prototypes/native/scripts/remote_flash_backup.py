#!/usr/bin/env python3
"""Read-only esptool worker for execution via SSH stdin on the physical USB host.

Caller supplies config to run(config), captures stdout DIRECTLY in the unlocked
vault, and captures stderr privately. No raw flash/config ever stored remotely.
Only identify and full backup modes; NO erase/write/reset-to-application path.
Opening/resetting into ROM and uploading a RAM stub require maintenance approval.
"""
import contextlib
import hashlib
import json
import sys


def run(config):
    import esptool
    import termios
    if config.get('maintenance_confirmed') is not True:
        raise ValueError('Attended maintenance acknowledgement required')
    if config.get('mode') not in ('identify', 'backup'):
        raise ValueError('Read-only operation required')
    esp = None
    with contextlib.redirect_stdout(sys.stderr):
        try:
            esp = esptool.detect_chip(port=config['port'], baud=115200)
            attrs = termios.tcgetattr(esp._port.fileno())
            attrs[2] &= ~termios.HUPCL
            termios.tcsetattr(esp._port.fileno(), termios.TCSANOW, attrs)
            mac = ':'.join(f'{x:02x}' for x in esp.read_mac())
            if esp.CHIP_NAME != 'ESP32-S3':
                raise ValueError('Only reviewed ESP32-S3 geometry supported')
            if config.get('expected_chip_mac') and mac != config['expected_chip_mac']:
                raise ValueError('Chip identity changed')
            security = esp.get_security_info()
            if security['parsed_flags']['SECURE_BOOT_EN'] or security['flash_crypt_cnt'].bit_count() % 2:
                raise ValueError('Secure/encrypted target requires separate review')
            esp = esp.run_stub()
            size = esptool.cmds.detect_flash_size(esp)
            if size != '16MB':
                raise ValueError('Only reviewed 16MB geometry supported')
            info = {'chip': esp.CHIP_NAME, 'expected_chip_mac': mac,
                    'flash_bytes': 16 * 1024 * 1024, 'flash_size': size,
                    'security': security, 'flash_writes_issued': False,
                    'application_reset_issued': False, 'ram_stub_uploaded': True,
                    'esptool_version': esptool.__version__}
            print('REMOTE_IDENTITY ' + json.dumps(info), flush=True)
            if config['mode'] == 'backup':
                if config.get('expected_chip_mac') != mac:
                    raise ValueError('Independent expected identity required for backup')
                esp.change_baud(460800)
                data = esp.read_flash(0, info['flash_bytes'])
                if len(data) != info['flash_bytes']:
                    raise ValueError('Incomplete full-flash read')
                device_md5 = esp.flash_md5sum(0, len(data))
                if hashlib.md5(data).hexdigest() != device_md5:
                    raise ValueError('Independent on-device digest did not match read')
                info.update(sha256=hashlib.sha256(data).hexdigest(), device_md5=device_md5,
                            verified=True, verification='independent device full-range MD5 matched read')
                print('REMOTE_BACKUP_VERIFIED ' + json.dumps(info), flush=True)
                # This is the REAL stdout, not redirected logging stdout. SSH
                # transports binary directly to the caller's vault file.
                sys.__stdout__.buffer.write(data)
                sys.__stdout__.buffer.flush()
        finally:
            if esp is not None:
                esp._port.close()  # No hard_reset: leave ROM/stub, never start old app.
    if config['mode'] == 'identify':
        sys.__stdout__.write(json.dumps(info) + '\n')
        sys.__stdout__.flush()
