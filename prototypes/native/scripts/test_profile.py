#!/usr/bin/env python3
"""Single-blob provisioning regression ONLY on the simulated spare; needs USB access."""
import argparse
import copy
import json
import time
import urllib.request
import urllib.error
from ota import Bench
from usb import Device, DEFAULT_PORT

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('host')
p.add_argument('--port', default=DEFAULT_PORT)
a = p.parse_args()
b = Bench(a.host)
d = Device(a.port)
assert d.request('GET', '/api/ota/status')['data']['boot_id'] == b.get('/api/ota/status')['boot_id'], 'USB/HTTP targets differ'
original = b.get('/api/profile')
original_source = b.get('/api/engine/status')['clock_source']


def post(path, value):
    req = urllib.request.Request(b.base + path, data=json.dumps(value).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with b.opener.open(req, timeout=8) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def ready():
    b.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')


try:
    ready()
    candidate = copy.deepcopy(original)
    candidate.update(hostname='bench-profile-test', timezone='UTC', clock_source='network')
    candidate['relays'] = [{'pin': 4, 'label': 'profile fixture', 'rule': 'return nil',
                            'auto': False, 'value': False, 'isInverted': True,
                            'defaultValue': True, 'defaultAuto': False}]
    candidate['sensor_pins'].update(i2c_scl=1, i2c_sda=2, light_switch=5)
    assert post('/api/profile/validate', candidate)[0] == 200
    assert b.get('/api/profile') == original
    bad = []
    for key, value in [('format_version', 2), ('hostname', 'Bad.Host'), ('timezone', 'unknown'),
                       ('clock_source', 'guess'), ('sensors_enabled', True), ('armed', True)]:
        item = copy.deepcopy(candidate)
        item[key] = value
        bad.append(item)
    item = copy.deepcopy(candidate); item['sensor_pins']['light_switch'] = 4; bad.append(item)
    item = copy.deepcopy(candidate); item['sensor_pins']['i2c_sda'] = -1; bad.append(item)
    item = copy.deepcopy(candidate); item['relays'][0]['pin'] = 19; bad.append(item)
    for item in bad:
        assert post('/api/profile/import', item)[0] == 400
        assert b.get('/api/profile') == original
    candidate['relays'][0]['unrelated_metadata'] = 'discard me'
    code, reply = post('/api/profile/import', candidate)
    assert code == 200 and reply['restart_required'] is True
    cfg = b.get('/api/config')
    assert cfg['hostname'] == 'bench-profile-test' and cfg['active_hostname'] == original['hostname']
    assert b.get('/api/profile')['clock_source'] == 'network'
    assert 'unrelated_metadata' not in b.get('/api/profile')['relays'][0]
    assert b.get('/api/engine/status')['electrical_levels'] == [{'pin': 4, 'level': True}]
    old_edit_boot=b.get('/api/profile/edit')['boot_id']
    d.reset(wait_healthy=False)
    forbidden = copy.deepcopy(candidate); forbidden['hostname'] = 'must-not-save'
    pending = d.request('POST', '/api/profile/import', json.dumps(forbidden))
    assert pending['status'] == 503
    assert d.request('POST', '/api/profile/patch', json.dumps({'expected_revision': '0'*64, 'expected_boot_id': '0'*16, 'changes': {'hostname': 'must-not-save'}}))['status'] == 503
    assert d.request('POST', '/api/time/config', json.dumps({'timezone': 'America/New_York'}))['status'] == 503
    assert d.request('POST', '/api/relays/config', json.dumps({'relays': []}))['status'] == 503
    ready()
    new_edit=b.get('/api/profile/edit')
    assert d.request('POST', '/api/profile/patch', json.dumps({'expected_revision': new_edit['revision'], 'expected_boot_id': old_edit_boot, 'changes': {'hostname': 'must-not-save'}}))['status'] == 409
    cfg = b.get('/api/config')
    assert cfg['hostname'] == cfg['active_hostname'] == 'bench-profile-test'
    assert cfg['restart_required'] is False
    restored = b.get('/api/profile')
    assert restored['timezone'] == 'UTC' and restored['clock_source'] == 'network'
    assert restored['sensor_pins'] == candidate['sensor_pins']
    assert restored['relays'][0]['value'] is True and restored['relays'][0]['auto'] is False
    assert b.get('/api/engine/status')['electrical_levels'] == [{'pin': 4, 'level': False}]
    assert b.get('/api/bench/io-status')['runtime_drives_gpio'] is False
    print('Profile validation, 9 rejection cases, pending-boot write gate, canonical export, identity/input/clock persistence and boot defaults PASS')
finally:
    try:
        d.wait_healthy()
        restored = d.request('POST', '/api/profile/import', json.dumps(original))
        assert restored['status'] == 200, 'Inspect device before any further mutation'
        d.reset(); ready()
        assert b.get('/api/config')['active_hostname'] == original['hostname']
        assert post('/api/bench/clock-source', {'source': original_source})[0] == 200
        print('Original complete profile and active identity restored; normal memory-only firmware retained')
    finally:
        d.close()
