#!/usr/bin/env python3
"""Read-only API snapshots, private vault only. NOT a flash/full-filesystem backup."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path('/var/lib/private-services/agent-state/jeremy/garden-device-backups')
ROUTES = ['config', 'sensor-config', 'relays/config', 'sensors', 'status', 'wifi/status', 'boards']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('devices', nargs='+', help='expected-hostname=IP')
args = parser.parse_args()
mount = subprocess.check_output(['findmnt', '-T', '/var/lib/private-services', '-no', 'SOURCE,TARGET'], text=True)
if '/dev/mapper/private-services /var/lib/private-services' not in mount:
    raise SystemExit('Private vault is not mounted; refusing unencrypted fallback')
os.umask(0o077)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
destination = ROOT / stamp
destination.mkdir(parents=True, exist_ok=False)

def fetch(ip, route):
    last = None
    for attempt in range(3):
        try:
            with opener.open(f'http://{ip}/api/{route}', timeout=5) as response:
                wire = response.read(65537)
                if len(wire) > 65536:
                    raise ValueError('API response exceeds backup limit')
                return json.loads(wire)
        except Exception as error:
            last = error
            if attempt < 2:
                time.sleep(1 + attempt)
    raise RuntimeError(f'GET {route} failed: {type(last).__name__}') from None

for specification in args.devices:
    name, ip = specification.split('=', 1)
    if not name.replace('-', '').isalnum() or any(c not in '0123456789.' for c in ip):
        raise SystemExit('Use a simple hostname and IPv4 address')
    folder = destination / name
    folder.mkdir()
    identity = fetch(ip, 'config')
    if identity.get('hostname') != name:
        raise SystemExit(f'{name}: hostname mismatch; stopping')
    manifest = {'device': name, 'address': ip, 'captured_at_utc': stamp, 'files': {}, 'errors': {},
                'limitations': ['API snapshot, not firmware or complete filesystem backup',
                                'Wi-Fi password and raw config.json not retrieved',
                                'Responses sampled sequentially, not an atomic device-wide snapshot']}
    for route in ROUTES:
        try:
            data = identity if route == 'config' else fetch(ip, route)
            wire = (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()
            filename = route.replace('/', '-') + '.json'
            (folder / filename).write_bytes(wire)
            manifest['files'][filename] = hashlib.sha256(wire).hexdigest()
        except Exception as error:
            manifest['errors'][route] = str(error)
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{name}: {len(manifest["files"])} API snapshots; missing routes={list(manifest["errors"])}')
print(f'Private snapshot directory: {destination}')
