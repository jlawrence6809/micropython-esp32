#!/usr/bin/env python3
"""Offline release-audit/image-parser checks. No device I/O."""
import copy
import hashlib
import struct
import unittest
from unittest import mock
import controller_release as release


def fixture():
    header = bytearray(24)
    header[0:2] = bytes((0xe9, 1)); header[23] = 1
    struct.pack_into('<H', header, 12, 9)
    descriptor = bytearray(256)
    struct.pack_into('<I', descriptor, 0, 0xabcd5432)
    descriptor[16:48] = release.CONTRACT.encode().ljust(32, b'\0')
    descriptor[48:80] = release.PROJECT.encode().ljust(32, b'\0')
    descriptor[144:176] = hashlib.sha256(b'test image').digest()
    image = header + struct.pack('<II', 0x3c000020, len(descriptor)) + descriptor
    checksum = 0xef
    for byte in descriptor:
        checksum ^= byte
    image += bytes((len(image) | 15) - len(image)) + bytes((checksum,))
    return bytes(image) + hashlib.sha256(image).digest()


def snapshot(active=True):
    ota = dict(boot_id='b'*16, elf_sha256='a'*64, healthy=True, running_state='valid',
               version=release.CONTRACT, runtime_watchdog_active=True, uploading=False,
               running_slot='ota_0', boot_slot='ota_0')
    return dict(config=dict(device_role='relay-controller', rule_language='lua', atomic_profile_edit=True, guarded_ota=True,
                            simulated=not active, restart_required=False, hostname='unit', active_hostname='unit'),
                io=dict(device_id='123456abcdef', layout_hash='c'*64, gpio_compiled=True,
                        gpio_active=active, armed_for_saved_layout=active, cleanup_failed=False,
                        backend_software_tests_passed=True),
                ota=ota, watchdog=dict(monitor_active=True, fault_injection=False, timeout_mask=0),
                edit=dict(ota, revision='d'*64), fence={'fence':'e'*64})


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.info = release.image_info(fixture())
        self.state = snapshot()

    def validate(self):
        return release.validate_snapshot(self.state, '123456abcdef', self.info)

    def test_image_integrity_and_contract(self):
        self.assertEqual(self.info['contract'], 'relay-profile1')
        self.assertEqual(self.info['image_sha256'], hashlib.sha256(fixture()).hexdigest())
        for offset in (0, 1, 12, 23, 24, 28, 32, 48, 80, 176, len(fixture())-33, len(fixture())-1):
            with self.subTest(offset=offset):
                bad = bytearray(fixture()); bad[offset] ^= 0x80
                with self.assertRaises(ValueError):
                    release.image_info(bad)
        for image in (fixture()[:-1], fixture()+b'\0', b'', fixture()[:200]):
            with self.assertRaises(ValueError):
                release.image_info(image)

    def test_active_and_inactive_consistent_states(self):
        for active in (True, False):
            self.state = snapshot(active)
            self.assertIs(self.validate()['gpio_active'], active)

    def test_fail_closed_fields(self):
        failures = [('config', 'device_role', 'development-bench'), ('config', 'simulated', True),
                    ('config', 'restart_required', True), ('config', 'active_hostname', 'other'),
                    ('config', 'atomic_profile_edit', False), ('config', 'guarded_ota', False), ('io', 'gpio_compiled', False),
                    ('io', 'cleanup_failed', True), ('io', 'backend_software_tests_passed', False),
                    ('io', 'device_id', 'ffffffffffff'), ('io', 'layout_hash', None),
                    ('io', 'armed_for_saved_layout', False), ('io', 'gpio_active', 'true'),
                    ('ota', 'boot_slot', 'ota_1'), ('ota', 'healthy', False), ('ota', 'uploading', True),
                    ('ota', 'version', 'native-profile1'), ('ota', 'running_state', 'pending'),
                    ('watchdog', 'fault_injection', True), ('watchdog', 'monitor_active', False),
                    ('watchdog', 'timeout_mask', 1), ('edit', 'revision', ''), ('edit', 'boot_id', 'e'*16), ('fence', 'fence', None)]
        for section, key, value in failures:
            with self.subTest(section=section, key=key):
                self.state = snapshot(); self.state[section][key] = value
                with self.assertRaises(ValueError):
                    self.validate()
                self.state = snapshot(); del self.state[section][key]
                with self.assertRaises(ValueError):
                    self.validate()

    def test_pending_arm_is_not_a_safe_update(self):
        self.state = snapshot(False); self.state['io']['armed_for_saved_layout'] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_noop_image_refused(self):
        self.state['ota']['elf_sha256'] = self.info['elf_sha256']
        self.state['edit']['elf_sha256'] = self.info['elf_sha256']
        with self.assertRaisesRegex(ValueError, 'already running'):
            self.validate()

    def test_inspect_gets_only_and_redacts(self):
        states = self.state
        def get(path):
            key = {'/api/ota/status':'ota', '/api/config':'config', '/api/io/status':'io',
                   '/api/watchdog/status':'watchdog', '/api/profile/edit':'edit', '/api/ota/fence':'fence'}[path]
            return copy.deepcopy(states[key])
        with mock.patch.object(release.urllib.request, 'urlopen', side_effect=AssertionError('unexpected I/O')):
            result = release.inspect(get, '123456abcdef', self.info)
        self.assertTrue(result['audit_passed'])
        self.assertFalse(result['upload_available'])
        self.assertNotIn('device_id', result)
        self.assertNotIn('revision', result)

    def test_change_between_snapshots_refused(self):
        calls = []
        def get(path):
            calls.append(path)
            key = {'/api/ota/status':'ota', '/api/config':'config', '/api/io/status':'io',
                   '/api/watchdog/status':'watchdog', '/api/profile/edit':'edit', '/api/ota/fence':'fence'}[path]
            data = copy.deepcopy(self.state[key])
            if key == 'edit' and len(calls) > 6:
                data['revision'] = 'e'*64
            return data
        with self.assertRaisesRegex(ValueError, 'changed during'):
            release.inspect(get, '123456abcdef', self.info)
        self.assertEqual(len(calls), 12)

    def test_transport_error_not_retried(self):
        get = mock.Mock(side_effect=TimeoutError())
        with self.assertRaises(TimeoutError):
            release.inspect(get, '123456abcdef', self.info)
        self.assertEqual(get.call_count, 1)


if __name__ == '__main__':
    unittest.main()
