#!/usr/bin/env python3
"""Attended, unloaded original-ESP32 initial flash; explicit fresh vault journal.
Never reset, arm, provision, retry a write or automatically start the application.
Only public artifacts may be staged remotely; private configuration arrives stdin.
"""
import contextlib
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate(config):
    from controller_release import image_info
    require(config.get('purpose') == 'relay-x8-original-esp32', 'Wrong purpose')
    require(all(config.get(k) is True for k in (
        'apply_confirmed', 'loads_disconnected', 'external_12v_confirmed',
        'adapter_power_pins_disconnected', 'backup_verified', 'remain_unarmed')),
        'Attended unloaded/backup/unarmed gates required')
    require(re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', config['expected_chip_mac']), 'Bad chip identity')
    require(re.fullmatch(r'[0-9a-f]{32}', config['original_device_md5']), 'Bad backup digest')
    require(config['expected_chip_revision'] == 301, 'Reviewed chip revision required')
    expected = {'0x1000': (0x7000, 'bootloader.bin'), '0x8000': (0x1000, 'partition-table.bin'),
                '0xf000': (0x2000, 'ota_data_initial.bin'), '0x20000': (0x180000, 'garden_native_probe.bin')}
    files = config['files']
    require(len(files) == 4 and {f['offset'] for f in files} == set(expected), 'Original ESP32 offsets required')
    blobs = {}; args = []
    for f in sorted(files, key=lambda x: int(x['offset'], 16)):
        limit, name = expected[f['offset']]
        require(f['file'] == name, 'Unexpected artifact filename')
        path = Path(config['artifact_directory']) / name
        require(not path.is_symlink(), 'Artifact symlink forbidden')
        b = path.read_bytes()
        require(0 < len(b) <= limit and len(b) == f['bytes'] and
                hashlib.sha256(b).hexdigest() == f['sha256'], 'Artifact changed/overlaps')
        blobs[f['offset']] = b
        args += [f['offset'], str(path)]
    require(image_info(blobs['0x20000'], 'esp32') == config['image'], 'Controller image audit mismatch')
    boot = blobs['0x1000']
    require(len(boot) >= 24 and boot[0] == 0xe9 and struct.unpack_from('<H', boot, 12)[0] == 0 and
            boot[2:4] == bytes([2, 0x20]), 'ESP32 DIO/40MHz/4MB bootloader required')
    entries = []
    table = blobs['0x8000']
    for off in range(0, len(table) - 31, 32):
        magic, typ, sub, addr, size = struct.unpack_from('<HBBII', table, off)
        if magic == 0x50aa:
            entries.append((typ, sub, addr, size))
        else:
            break
    require(entries == [(1,2,0x9000,0x6000), (1,0,0xf000,0x2000), (1,1,0x11000,0x1000),
                        (0,0x10,0x20000,0x180000), (0,0x11,0x1a0000,0x180000)], 'Wrong partition layout')
    require(blobs['0xf000'] == b'\xff' * 8192, 'Initial OTA data must be blank')
    return args, blobs


@contextlib.contextmanager
def guard_port(config):
    import fcntl
    import os
    import subprocess
    require(os.uname().nodename == 'drallion', 'Physical USB host mismatch')
    port = Path(config['port'])
    require(str(port) == '/dev/serial/by-path/pci-0000:00:14.0-usb-0:7:1.0-port0', 'USB topology changed')
    tty = port.resolve(strict=True)
    parents = Path('/sys/class/tty/' + tty.name + '/device').resolve().parents
    usb = next(p for p in parents if (p / 'idVendor').exists())
    require(usb == Path('/sys/bus/usb/devices/3-7').resolve() and
            (usb/'idVendor').read_text().strip() == '067b' and
            (usb/'idProduct').read_text().strip() == '2303', 'Adapter USB identity changed')
    with open('/tmp/garden-uart-adapter-test.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check = subprocess.run(['fuser', str(tty)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        require(check.returncode == 1 and not check.stdout.strip(), 'TTY owned or ownership check failed')
        yield


def run(config):
    args, blobs = validate(config)  # Before serial imports/open or any mutation.
    import esptool
    import serial
    import termios
    def emit(stage, **more):
        sys.__stdout__.write(json.dumps(dict(stage=stage, **more)) + '\n')
        sys.__stdout__.flush()
    with guard_port(config), contextlib.redirect_stdout(sys.stderr):
        port = serial.Serial(port=None, baudrate=115200, timeout=.25, write_timeout=8, exclusive=True)
        port.dtr = False; port.rts = False; port.port = config['port']
        try:
            emit('serial_open_started')
            port.open()
            attrs = termios.tcgetattr(port.fileno()); attrs[2] &= ~termios.HUPCL
            termios.tcsetattr(port.fileno(), termios.TCSANOW, attrs)
            esp = esptool.ESP32ROM(port, baud=115200)
            esp.connect(mode='no_reset', attempts=1)
            require(esp.CHIP_NAME == 'ESP32' and ':'.join(f'{x:02x}' for x in esp.read_mac()) == config['expected_chip_mac'] and
                    esp.get_chip_revision() == config['expected_chip_revision'], 'Chip identity mismatch; no erase')
            require(not esp.secure_download_mode and not esp.get_secure_boot_enabled() and
                    not esp.get_flash_encryption_enabled() and not esp.get_encrypted_download_disabled(),
                    'Unsupported security; no erase')
            esp = esp.run_stub()  # Reuses existing stub when sync detects it.
            esp.WRITE_FLASH_ATTEMPTS = 1
            esptool.loader.WRITE_BLOCK_ATTEMPTS = 1
            require(esptool.cmds.detect_flash_size(esp) == '4MB', 'Wrong flash geometry; no erase')
            require(esp.flash_md5sum(0, 4194304) == config['original_device_md5'], 'Flash changed since backup; no erase')
            emit('identity_security_geometry_original_digest_verified', baud=115200, write_attempts=1)
            base = ['--chip','esp32','--baud','115200','--before','no_reset','--no-stub','--after','no_reset_stub']
            for stage, extra in (
                ('erase', ['erase_flash']),
                ('write', ['write_flash','--flash_mode','dio','--flash_freq','40m','--flash_size','4MB'] + args),
                ('verify', ['verify_flash','--diff','no'] + args)):
                emit(stage + '_started')
                esptool.main(base + extra, esp=esp)
                emit(stage + '_completed')
            for offset, b in blobs.items():
                require(esp.flash_md5sum(int(offset,16), len(b)) == hashlib.md5(b).hexdigest(), 'Device artifact digest mismatch; inspect no replay')
            require(esp.flash_md5sum(0x9000, 0x6000) == hashlib.md5(b'\xff'*0x6000).hexdigest(), 'NVS not erased')
            emit('flash_verified_waiting_operator_en', flash_writes_verified=True, nvs_erased=True,
                 arming_issued=False, provision_issued=False, reset_commands=0, application_started=False)
        except BaseException as e:
            emit('stopped_inspect_no_replay', error_type=type(e).__name__)
            raise
        finally:
            port.close()
            emit('serial_closed')


if __name__ == '__main__':
    run(json.load(sys.stdin))
