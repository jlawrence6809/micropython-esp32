#!/usr/bin/env python3
"""Pure I/O-plan API checks on the spare. Never applies hardware settings."""
import argparse
import copy
import json
import urllib.error
import urllib.request
from ota import Bench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('host')
parser.add_argument('--expect-physical-selftest', action='store_true',
                    help='Expect the dedicated disconnected-spare diagnostic build')
args = parser.parse_args()
bench = Bench(args.host)
status = bench.get('/api/bench/io-status')
assert status['tested'] and status['passed']
assert status['runtime_drives_gpio'] is False
assert status['physical_selftest_ran'] is args.expect_physical_selftest
assert status['cases'] == (17 if args.expect_physical_selftest else 13), status
assert status['test_pins_released'] is (True if args.expect_physical_selftest else None)
sensors = {k: -1 for k in ('i2c_scl', 'i2c_sda', 'ds18b20', 'photo_sensor', 'light_switch', 'reset_switch')}
relays = [{'pin': p, 'isInverted': inv, 'defaultValue': value} for p, inv, value in
          [(4, False, False), (5, False, True), (6, True, False), (7, True, True)]]
original = bench.get('/api/relays/config')

def plan(body):
    req = urllib.request.Request(bench.base + '/api/bench/io-plan', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with bench.opener.open(req, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

code, result = plan({'relays': relays, 'sensor_pins': sensors})
assert code == 200 and result['hardware_applied'] is False
assert [r['boot_level'] for r in result['relay_boot_levels']] == [0, 1, 1, 0]
for label, change in [
    ('duplicate output', lambda x: x['relays'].append(copy.deepcopy(x['relays'][0]))),
    ('output/input collision', lambda x: x['sensor_pins'].update(light_switch=4)),
    ('incomplete I2C', lambda x: x['sensor_pins'].update(i2c_scl=1)),
    ('same I2C pins', lambda x: x['sensor_pins'].update(i2c_scl=1, i2c_sda=1)),
    ('reserved pin', lambda x: x['relays'][0].update(pin=43)),
    ('unsupported 1wire', lambda x: x['sensor_pins'].update(ds18b20=8)),
    ('unsupported ADC', lambda x: x['sensor_pins'].update(photo_sensor=8)),
    ('invalid boolean', lambda x: x['relays'][0].update(isInverted='yes')),
]:
    body = copy.deepcopy({'relays': relays, 'sensor_pins': sensors})
    change(body)
    assert plan(body)[0] == 400, label
assert bench.get('/api/relays/config') == original
print('I/O plan/boot-level matrix and 8 rejection cases PASS; no hardware/settings applied')
print('Boot I/O tests:', status)
