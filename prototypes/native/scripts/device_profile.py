#!/usr/bin/env python3
"""Credential-free configuration export/validate/import for the simulated spare."""
import argparse
import json
import os
import urllib.request
from pathlib import Path
from ota import Bench

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('host')
p.add_argument('action', choices=('export', 'validate', 'import'))
p.add_argument('file', type=Path)
p.add_argument('--apply', action='store_true', help='Explicitly permit a configuration write')
a = p.parse_args()
if a.action == 'import' and not a.apply:
    p.error('Import requires --apply; use validate first')
if a.action == 'export' and not a.file.name.endswith('.local.json'):
    p.error('Export filename must end in .local.json (gitignored private configuration)')
b = Bench(a.host)
if a.action == 'export':
    wire = (json.dumps(b.get('/api/profile'), indent=2) + '\n').encode()
    fd = os.open(a.file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(wire)
    print('Private credential-free profile exported; existing files are never overwritten')
else:
    data = json.dumps(json.loads(a.file.read_text())).encode()
    endpoint = '/api/profile/validate' if a.action == 'validate' else '/api/profile/import'
    if a.action == 'import':
        b.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
    req = urllib.request.Request(b.base + endpoint, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with b.opener.open(req, timeout=8) as response:
            result = json.load(response)
    except Exception:
        if a.action == 'import':
            print('Import completion may be uncertain. Inspect /api/profile over HTTP/USB before retrying.')
        raise
    if not result.get('success'):
        raise SystemExit('Profile operation failed; inspect device state')
    print('Profile', a.action, 'PASS; restart_required=', result['restart_required'], '; no GPIO enabled')
