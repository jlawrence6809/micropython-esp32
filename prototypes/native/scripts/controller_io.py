#!/usr/bin/env python3
"""USB-only controller arming metadata. No automatic reboot or hardware test."""
import argparse
import json
from usb import Device, DEFAULT_PORT

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('action', choices=('status', 'arm', 'disarm'))
p.add_argument('--port', default=DEFAULT_PORT)
p.add_argument('--expected-layout')
p.add_argument('--expected-boot-id')
p.add_argument('--expected-device-id')
p.add_argument('--confirm-maintenance-window', action='store_true')
a = p.parse_args()
if not a.confirm_maintenance_window:
    p.error('All controller USB access needs --confirm-maintenance-window: opening the adapter can reset hardware')
if a.action != 'status' and not (a.confirm_maintenance_window and a.expected_layout and a.expected_boot_id and a.expected_device_id):
    p.error('Mutation requires --confirm-maintenance-window, --expected-layout, --expected-boot-id and --expected-device-id')
d = Device(a.port, controller=True)
try:
    io = d.request('GET', '/api/io/status')['data']
    boot = d.request('GET', '/api/ota/status')['data']
    if a.action == 'status':
        print(json.dumps(dict(io, boot_id=boot['boot_id'], healthy=boot['healthy']), indent=2))
    else:
        if a.expected_layout != io['layout_hash'] or a.expected_boot_id != boot['boot_id'] or a.expected_device_id != io['device_id']:
            raise SystemExit('Controller boot/layout changed; inspect before any mutation')
        phrase = ('enable' if a.action == 'arm' else 'disable') + ' relay outputs after reboot'
        try:
            reply = d.command({'op': 'io_' + a.action, 'layout_hash': a.expected_layout, 'device_id': a.expected_device_id, 'boot_id': a.expected_boot_id, 'confirm': phrase})
        except (TimeoutError, OSError, ValueError):
            print('Completion uncertain. Inspect arming state before retrying; this tool issued no reboot command.')
            raise
        if reply['status'] != 200 or not reply['data'].get('success'):
            raise SystemExit('Arming metadata write failed; inspect state over USB before retrying')
        print(reply['data']['message'])
        print('No reboot issued. Review electrical/maintenance plan before resetting the controller.')
finally:
    d.close()
