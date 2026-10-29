#!/usr/bin/env python3
"""Guarded OTA reservation tests ONLY on the disconnected normal memory-only spare.

Opens the verified spare USB (can reset it). Streams/aborts an inactive-slot
partial image but never selects it or requests a reset. No mutation is retried.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import time
import urllib.error
import urllib.request
from ota import Bench, image_elf_hash
from usb import Device, DEFAULT_PORT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('host'); p.add_argument('image', type=Path)
    p.add_argument('--port', default=DEFAULT_PORT)
    p.add_argument('--confirm-memory-only-spare', action='store_true')
    a = p.parse_args()
    if not a.confirm_memory_only_spare:
        p.error('Explicit disconnected memory-only spare confirmation required')
    b = Bench(a.host)
    assert b.get('/api/io/status')['gpio_compiled'] is False
    assert b.get('/api/watchdog/status')['fault_injection'] is False
    assert b.get('/api/bench/io-status')['physical_selftest_ran'] is False
    image = a.image.read_bytes()
    assert image[48:80].split(b'\0', 1)[0] == b'native-profile1'
    assert b.get('/api/ota/status')['elf_sha256'] == image_elf_hash(image)
    d = Device(a.port)
    try:
        d.wait_healthy()
        before = b.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
        original = b.get('/api/profile')
        assert b.get('/api/config')['guarded_ota'] is True
        def token(): return b.get('/api/ota/fence')['fence']
        first = token()
        assert token() == first
        # Explicit no-op must invalidate a previously read OTA token.
        assert d.request('POST', '/api/profile/import', json.dumps(original))['status'] == 200
        current = token(); assert first != current
        def rejected(fence):
            prefix = image[:288]
            req = urllib.request.Request(b.base+'/api/ota/upload', data=prefix,
                headers={'Content-Type':'application/octet-stream', 'X-Firmware-SHA256':hashlib.sha256(prefix).hexdigest(), 'X-Garden-OTA-Fence':fence})
            try:
                with b.opener.open(req, timeout=8): raise AssertionError('Bad fence accepted')
            except urllib.error.HTTPError as error:
                assert error.code == 409
                error.close()
        rejected(first); rejected('0'*64)
        assert token() == current
        selected = b.get('/api/ota/status')
        assert selected['boot_id'] == before['boot_id'] and selected['boot_slot'] == before['boot_slot']
        edit = b.get('/api/profile/edit')
        request = dict(expected_revision=edit['revision'], expected_boot_id=edit['boot_id'], changes={'hostname':original['hostname']})
        with socket.create_connection((a.host, 80), timeout=4) as sock:
            headers = (f'POST /api/ota/upload HTTP/1.1\r\nHost: {a.host}\r\nContent-Type: application/octet-stream\r\n'
                       f'Content-Length: {len(image)}\r\nX-Firmware-SHA256: {hashlib.sha256(image).hexdigest()}\r\n'
                       f'X-Garden-OTA-Fence: {current}\r\nConnection: close\r\n\r\n').encode()
            sock.sendall(headers+image[:1024])
            deadline = time.monotonic()+15
            # Short read RPCs fit the UART FIFO during initial flash erase.
            # Wait for the receive-loop phase before sending larger negative
            # test RPCs: non-IRAM UART RX may drop long frames during flash erase.
            while not d.request('GET', '/api/ota/status')['data']['image_streaming']:
                assert time.monotonic()<deadline
                time.sleep(.02)
            # USB executes independently of HTTP; these must return promptly,
            # proving no runtime mutex is held across the blocked image receive.
            for path, body in (('/api/profile/patch', request), ('/api/profile/import', original),
                               ('/api/relays/config', {'relays':original['relays']}),
                               ('/api/time/config', {'timezone':'UTC'}),
                               ('/api/relays/control', {'label':original['relays'][0]['label'], 'state':original['relays'][0]['value']})):
                assert d.request('POST', path, json.dumps(body))['status'] == 503, path
            assert d.command({'op':'io_arm'})['status'] == 503
            assert d.command({'op':'io_disarm'})['status'] == 503
            assert d.command({'op':'provision'})['status'] == 503
            assert d.request('GET', '/api/ota/fence')['status'] == 409
        # Closed stream must release reservation without changing boot selection.
        after = b.wait(lambda s: not s['uploading'] and s['healthy'])
        assert after['boot_id'] == before['boot_id'] and after['elf_sha256'] == before['elf_sha256']
        assert after['boot_slot'] == before['boot_slot'] and after['running_slot'] == before['running_slot']
        assert b.get('/api/profile') == original and token() == current
        assert d.request('POST', '/api/profile/import', json.dumps(original))['status'] == 200
        assert token() != current
        print('OTA fence PASS: stale/no-op invalidation, mismatch rejection, streaming reservation, eight USB persistent/manual/arming/credential gates, abort release; same healthy boot/profile, no GPIO')
    finally:
        d.close()


if __name__ == '__main__':
    main()
