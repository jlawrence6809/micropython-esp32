#!/usr/bin/env python3
"""Reject/interruption tests that write ONLY an inactive spare flash slot."""
import argparse
import hashlib
import socket
import time
from pathlib import Path
from ota import Bench, image_elf_hash

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('host')
parser.add_argument('image', type=Path)
args = parser.parse_args()
bench = Bench(args.host)
image = args.image.read_bytes()
image_elf_hash(image)
before = bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
configuration = bench.get('/api/relays/config')
profile = bench.get('/api/profile')

def unchanged():
    after = bench.wait(lambda s: not s['uploading'] and s['healthy'])
    for field in ('running_slot', 'boot_slot', 'elf_sha256'):
        assert before[field] == after[field], field
    assert bench.get('/api/relays/config') == configuration
    assert bench.get('/api/profile') == profile

# Malformed format and wrong project rejected before staging.
for label, payload in [('format', bytes(1024)),
                       ('project', image[:80] + b'other_project'.ljust(32, b'\0') + image[112:1024]),
                       ('configuration-contract', image[:48] + b'pre-profile'.ljust(32, b'\0') + image[80:1024]) ]:
    status, result = bench.upload(payload)
    assert status == 400, (label, status, result)
    unchanged()
    print(label, 'rejection PASS')

# Correct image but wrong transport digest: no boot selection change.
status, result = bench.upload(image, '0' * 64)
assert status == 400, result
unchanged()
print('digest mismatch PASS')

# Correct transport digest, corrupt embedded image checksum/hash.
corrupt = bytearray(image)
corrupt[4096] ^= 1
status, result = bench.upload(bytes(corrupt))
assert status == 400, result
unchanged()
print('image-integrity rejection PASS')

# Disconnect after a valid prefix, well short of the declared image size.
with socket.create_connection((args.host, 80), timeout=5) as connection:
    header = (f'POST /api/ota/upload HTTP/1.1\r\nHost: {args.host}\r\n'
              f'Content-Length: {len(image)}\r\nContent-Type: application/octet-stream\r\n'
              f'X-Firmware-SHA256: {hashlib.sha256(image).hexdigest()}\r\nConnection: close\r\n\r\n').encode()
    connection.sendall(header + image[:8192])
time.sleep(4)
unchanged()
print('interrupted upload PASS; running firmware and configuration unchanged')
