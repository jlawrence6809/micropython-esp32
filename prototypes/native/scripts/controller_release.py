#!/usr/bin/env python3
"""Read-only controller release audit. Deliberately has NO upload/reset/arm path.

Offline image checks work without a device. Online checks use GET only, require
an explicit expected chip ID, and refuse bench/ambiguous/pending-activation states.
This is a review aid, not authorization to operate connected equipment.
"""
import argparse
import hashlib
import ipaddress
import json
import re
import struct
import urllib.request
from pathlib import Path

CONTRACT = 'relay-profile1'
PROJECT = 'garden_native_probe'
MAX_IMAGE = 0x300000  # Historical S3 slot; original ESP32 is an explicit opt-in.
TARGETS = {'esp32s3': (9, MAX_IMAGE), 'esp32': (0, 0x180000)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hex_string(value, length):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def image_info(image, chip_target='esp32s3'):
    require(chip_target in TARGETS, 'Unsupported chip target')
    chip_id, slot_bytes = TARGETS[chip_target]
    require(288 <= len(image) <= slot_bytes, 'Image size outside controller slot bounds')
    require(image[0] == 0xe9 and 1 <= image[1] <= 16, 'Invalid ESP image header')
    require(struct.unpack_from('<H', image, 12)[0] == chip_id, chip_target + ' image required')
    require(image[23] == 1, 'Appended image SHA256 required')
    require(struct.unpack_from('<I', image, 32)[0] == 0xabcd5432, 'Missing first-segment app descriptor')
    require(image[48:80] == CONTRACT.encode().ljust(32, b'\0'), 'Controller configuration contract required; bench images forbidden')
    require(image[80:112] == PROJECT.encode().ljust(32, b'\0'), 'Wrong application project')
    cursor = 24
    checksum = 0xef
    for segment in range(image[1]):
        require(cursor + 8 <= len(image), 'Truncated segment header')
        _, size = struct.unpack_from('<II', image, cursor)
        require(segment != 0 or size >= 256, 'First segment cannot contain app descriptor')
        cursor += 8
        require(cursor + size <= len(image), 'Truncated segment data')
        for byte in image[cursor:cursor+size]:
            checksum ^= byte
        cursor += size
    checksum_at = cursor | 15
    require(checksum_at + 33 == len(image), 'Unexpected image length/trailer')
    require(not any(image[cursor:checksum_at]), 'Invalid image padding')
    require(image[checksum_at] == checksum, 'Image segment checksum mismatch')
    require(hashlib.sha256(image[:checksum_at+1]).digest() == image[checksum_at+1:], 'Appended image SHA256 mismatch')
    return {'contract': CONTRACT, 'project': PROJECT, 'bytes': len(image),
            'chip_target': chip_target, 'image_chip_id': chip_id,
            'image_sha256': hashlib.sha256(image).hexdigest(), 'elf_sha256': image[176:208].hex()}


def controller_state(snapshot, expected_device_id):
    cfg, io, ota, wd, edit = (snapshot[key] for key in ('config', 'io', 'ota', 'watchdog', 'edit'))
    require(cfg.get('device_role') == 'relay-controller' and cfg.get('rule_language') == 'lua' and
            cfg.get('atomic_profile_edit') is True and cfg.get('guarded_ota') is True and io.get('gpio_compiled') is True, 'Not a supported controller')
    require(hex_string(expected_device_id, 12) and io.get('device_id') == expected_device_id, 'Expected device ID mismatch')
    require(io.get('cleanup_failed') is False and io.get('backend_software_tests_passed') is True, 'I/O cleanup/selftest failure or missing metadata')
    require(io.get('persistence_uncertain') is not True and io.get('outputs_applied') is not False, 'Persistence/output application uncertain; inspect before OTA')
    active, armed = io.get('gpio_active'), io.get('armed_for_saved_layout')
    require(type(active) is bool and type(armed) is bool and active == armed, 'Pending arm/disarm or inconsistent activation; do not use OTA as activation/reboot')
    require(cfg.get('simulated') is (not active), 'Inconsistent output-mode metadata')
    require(cfg.get('restart_required') is False and cfg.get('hostname') == cfg.get('active_hostname') and
            isinstance(cfg.get('hostname'), str), 'Deferred identity change; resolve separately')
    require(ota.get('version') == CONTRACT and ota.get('healthy') is True and ota.get('running_state') == 'valid' and
            ota.get('runtime_watchdog_active') is True and ota.get('uploading') is False, 'Not a healthy, idle controller image')
    require(ota.get('running_slot') in ('ota_0', 'ota_1') and ota.get('boot_slot') == ota.get('running_slot'), 'Boot selection already changed')
    require(wd.get('monitor_active') is True and wd.get('fault_injection') is False and wd.get('timeout_mask') == 0, 'Watchdog/fault state not normal')
    require(edit.get('healthy') is True and edit.get('running_state') == 'valid' and edit.get('boot_id') == ota.get('boot_id') and
            edit.get('elf_sha256') == ota.get('elf_sha256'), 'Edit snapshot/boot mismatch')
    for value, length in ((ota.get('boot_id'), 16), (ota.get('elf_sha256'), 64), (io.get('layout_hash'), 64), (edit.get('revision'), 64)):
        require(hex_string(value, length), 'Missing/malformed identity or edit fence')
    require(hex_string(snapshot.get('fence', {}).get('fence'), 64), 'Missing server OTA consistency fence')
    return {'ota_fence': snapshot['fence']['fence'], 'device_id': io['device_id'], 'boot_id': ota['boot_id'], 'layout_hash': io['layout_hash'],
            'revision': edit['revision'], 'running_elf': ota['elf_sha256'], 'running_slot': ota['running_slot'],
            'gpio_active': active}


def validate_image_target(snapshot, image):
    ota = snapshot['ota']
    target = image.get('chip_target', 'esp32s3')
    require(target in TARGETS, 'Unsupported image target')
    # Old deployed S3 firmware lacks these fields. Only S3 may use that legacy
    # fallback; original ESP32 always needs explicit, coherent target/slot data.
    chip_id = ota.get('image_chip_id', 9)
    require(ota.get('chip_target', 'esp32s3') == target and type(chip_id) is int and
            chip_id == TARGETS[target][0], 'Controller/image chip target mismatch')
    if target == 'esp32' or 'chip_target' in snapshot['config']:
        require(snapshot['config'].get('chip_target') == target, 'Configuration/OTA chip target mismatch')
    size = ota.get('update_partition_bytes')
    require(target != 'esp32' or size is not None, 'ESP32 update slot metadata required')
    if size is not None:
        require(type(size) is int and 288 <= image['bytes'] <= size, 'Image exceeds actual inactive slot')


def validate_snapshot(snapshot, expected_device_id, image):
    state = controller_state(snapshot, expected_device_id)
    validate_image_target(snapshot, image)
    require(image['elf_sha256'] != state['running_elf'], 'Image already running; no reason for a maintenance reset')
    return state


def inspect(get, expected_device_id, image):
    def snapshot():
        return {name: get(path) for name, path in (
            ('ota', '/api/ota/status'), ('config', '/api/config'), ('io', '/api/io/status'),
            ('watchdog', '/api/watchdog/status'), ('edit', '/api/profile/edit'), ('fence', '/api/ota/fence'))}
    first = validate_snapshot(snapshot(), expected_device_id, image)
    second = validate_snapshot(snapshot(), expected_device_id, image)
    require(first == second, 'Controller changed during inspection; no automatic retry/rebase')
    # Do not print profiles, labels, configured names, addresses or identity tokens.
    fingerprint = hashlib.sha256(json.dumps({'fence': second, 'image': image}, sort_keys=True).encode()).hexdigest()
    return {'audit_passed': True, 'current_gpio_active': second['gpio_active'], 'review_fingerprint': fingerprint,
            'image': image, 'upload_available': False,
            'warning': 'Server reservation supported; controller execution still review-gated. No update/reset/arming issued.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('--chip-target', choices=tuple(TARGETS), default='esp32s3', help='Original ESP32 must be selected explicitly')
    p.add_argument('--host', help='Literal IPv4 controller address; GET-only audit')
    p.add_argument('--expected-device-id', help='Previously independently verified 12-hex chip ID')
    a = p.parse_args()
    info = image_info(a.image.read_bytes(), a.chip_target)  # Before any network request.
    if a.host:
        require(isinstance(ipaddress.ip_address(a.host), ipaddress.IPv4Address), 'Literal IPv4 required')
        require(hex_string(a.expected_device_id, 12), '--expected-device-id required for online audit')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def get(path):
            with opener.open('http://' + a.host + path, timeout=4) as response:
                return json.load(response)  # Single attempt; no retries, no mutation methods.
        result = inspect(get, a.expected_device_id, info)
    else:
        require(a.expected_device_id is None, 'Expected device ID requires --host')
        result = {'offline_image_valid': True, 'image': info, 'upload_available': False}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
