#!/usr/bin/env python3
"""LAN-only updates for the verified simulated spare; never retries an upload."""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


class Bench:
    def __init__(self, host):
        if any(c in host for c in '/@?#'):
            raise ValueError('Use an IP or hostname, not a URL')
        self.base = 'http://' + host
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        cfg = verify_read(self, '/api/config')
        if cfg.get('simulated') is not True or not (
                cfg.get('device_role') == 'development-bench' or
                (not cfg.get('device_role') and cfg.get('hostname') == 'garden-bench')):
            raise RuntimeError('Not the simulated spare; refusing any update')

    def get(self, path):
        with self.opener.open(self.base + path, timeout=4) as response:
            return json.load(response)

    def upload(self, image, digest=None, fence=None):
        headers = {'Content-Type': 'application/octet-stream',
                   'X-Firmware-SHA256': digest or hashlib.sha256(image).hexdigest()}
        if fence is not None:
            headers['X-Garden-OTA-Fence'] = fence
        request = urllib.request.Request(self.base + '/api/ota/upload', data=image, headers=headers)
        try:
            with self.opener.open(request, timeout=135) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def wait(self, predicate, timeout=75):
        end = time.monotonic() + timeout
        last = None
        while time.monotonic() < end:
            try:
                last = self.get('/api/ota/status')
                if predicate(last):
                    return last
            except (OSError, ValueError):
                pass
            time.sleep(1)
        raise TimeoutError(f'Expected OTA state not observed; last status={last}. Do not blindly retry upload.')


def verify_read(bench, path):
    """Bounded transport retries for read-only checks; never replay a mutation."""
    for attempt in range(3):
        try:
            return bench.get(path)
        except urllib.error.HTTPError:
            raise
        except OSError as error:
            if attempt == 2:
                raise
            print(f'Read-only verification retry for {path} ({type(error).__name__}); no mutation/upload replay')
            time.sleep(0.5)


def image_elf_hash(image):
    if len(image) < 288 or image[0] != 0xE9 or image[80:112].split(b'\0', 1)[0] != b'garden_native_probe':
        raise ValueError('Not a native prototype application binary')
    return image[176:208].hex()


def update(bench, image, rollback=False, guarded=False):
    expected_sha = image_elf_hash(image)
    before = bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
    configuration = bench.get('/api/relays/config')['relays']
    prior_profile = None
    try:
        prior_profile = bench.get('/api/profile')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    prior_clock = None
    try:
        prior_clock = bench.get('/api/time/status')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    if rollback and before['elf_sha256'] == expected_sha:
        raise ValueError('Rollback test image must differ from the running firmware')
    fence = bench.get('/api/ota/fence')['fence'] if guarded else None
    try:
        status, response = bench.upload(image, fence=fence) if guarded else bench.upload(image)
    except (OSError, ValueError) as error:
        # A lost response does not establish failure: inspect, never auto-replay.
        print(f'Upload completion uncertain ({type(error).__name__}); inspecting boot status without retrying')
    else:
        if status != 200 or not response.get('success'):
            raise RuntimeError(f'Update rejected: {status} {response}')
        print('Image accepted; waiting for health validation/rollback')
    if rollback:
        after = bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid'
                           and s['running_slot'] == before['running_slot']
                           and s['elf_sha256'] == before['elf_sha256']
                           and s['update_state'] == 'aborted'
                           and (not before.get('boot_id') or s.get('boot_id') != before['boot_id']))
    else:
        after = bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid'
                           and s['running_slot'] != before['running_slot']
                           and s['elf_sha256'] == expected_sha
                           and (not before.get('boot_id') or s.get('boot_id') != before['boot_id']))
    restored = verify_read(bench, '/api/relays/config')['relays']
    assert len(configuration) == len(restored)
    for old, new in zip(configuration, restored, strict=True):
        for key in ('pin', 'label', 'rule', 'isInverted', 'defaultValue', 'defaultAuto'):
            assert old[key] == new[key], 'Relay configuration changed across OTA'
        assert new['auto'] is new['defaultAuto']
        # Immediate constant rules may validly change a default output after boot.
    assert verify_read(bench, '/api/wifi/status')['provisioned'] is True
    if prior_profile is not None:
        profile = verify_read(bench, '/api/profile')
        for key in prior_profile:
            if key != 'relays':
                assert profile[key] == prior_profile[key], 'Device profile changed across OTA'
    if prior_clock is not None:
        assert verify_read(bench, '/api/time/status')['timezone'] == prior_clock['timezone']
    print(('ROLLBACK' if rollback else 'OTA'), 'PASS:', before['running_slot'], '->', after['running_slot'],
          'state=', after['running_state'], 'configuration and Wi-Fi retained')
    return after


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host')
    parser.add_argument('image', type=Path)
    parser.add_argument('--expect-rollback', action='store_true', help='Only for the intentional pending-boot failure build')
    parser.add_argument('--guarded', action='store_true', help='Use the server-enforced public boot/profile/arming consistency fence (still bench-only)')
    args = parser.parse_args()
    update(Bench(args.host), args.image.read_bytes(), args.expect_rollback, args.guarded)
