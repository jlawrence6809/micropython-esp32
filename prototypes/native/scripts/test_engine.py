#!/usr/bin/env python3
"""Shared control-loop and clock-guard tests; all outputs stay in RAM."""
import copy
import json
import time
import urllib.error
import urllib.request
import argparse
from ota import Bench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('host')
args = parser.parse_args()
b = Bench(args.host)
original = b.get('/api/relays/config')['relays']
original_source = b.get('/api/engine/status')['clock_source']
original_zone = b.get('/api/time/status')['timezone']
assert b.get('/api/engine/status')['backend'] == 'memory-only'


def post(path, obj):
    req = urllib.request.Request(b.base + path, data=json.dumps(obj).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with b.opener.open(req, timeout=8) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def relay(rule, **kwargs):
    return dict({'pin': 4, 'label': 'engine-test', 'isInverted': True, 'value': False,
                 'auto': True, 'defaultValue': False, 'defaultAuto': False, 'rule': rule}, **kwargs)


def frame(local, utc, mono, **inputs):
    clock = {'valid': local is not None, 'monotonic_ms': mono}
    if local is not None:
        clock.update(local_seconds=local, unix_seconds=1893456000 + utc)
    return {'inputs': inputs, 'clock': clock}


def trace(r, frames):
    code, result = post('/api/bench/engine-run', {'relays': [r], 'frames': frames})
    assert code == 200 and result['success'], result
    return result


scheduled = '''local s = get_switch_state() and not get_last_switch_state()
local off = not get_switch_state() and get_last_switch_state()
local t, p = get_time(), get_last_time()
local on_time, off_time = false, false
if t ~= nil and p ~= nil then
 on_time = p < time(14,0) and time(14,0) <= t
 off_time = p < time(22,0) and time(22,0) <= t
end
if s or on_time then return true end
if off or off_time then return false end
return nil'''

r = trace(relay(scheduled), [frame(50399, 50399, 0), frame(50400, 50400, 1000),
                              frame(79199, 79199, 2000), frame(79200, 79200, 3000)])
assert [f['outputs'][0]['value'] for f in r['frames']] == [False, True, True, False]
assert [f['outputs'][0]['level'] for f in r['frames']] == [True, False, False, True]
assert r['writes'] == 2 and r['discontinuities'] == 1

# A delayed initial sync or large forward jump must not replay past transitions.
r = trace(relay(scheduled), [frame(None, 0, 0), frame(54000, 54000, 1000),
                              frame(50399, 50399, 2000), frame(79201, 79201, 3000)])
assert all(not f['outputs'][0]['value'] for f in r['frames'])
assert r['writes'] == 0 and r['discontinuities'] == 2

# Switch edges remain functional without a clock.
r = trace(relay(scheduled), [frame(None, 0, 0), frame(None, 0, 1000, switch_state=True),
                              frame(None, 0, 2000, switch_state=True),
                              frame(None, 0, 3000, switch_state=False)])
assert [f['outputs'][0]['value'] for f in r['frames']] == [False, True, True, False]
assert r['writes'] == 2

# Clock loss, midnight, DST-like local jumps and non-monotonic uptime are isolated.
for frames, last in [
    ([frame(86399, 86399, 0), frame(0, 86400, 1000)], 86399),
    ([frame(7199, 7199, 0), frame(10800, 7200, 1000)], -1),
    ([frame(7199, 7199, 1000), frame(7200, 7200, 0)], -1),
    ([frame(50399, 50399, 0), frame(None, 0, 1000), frame(50400, 50400, 2000)], -1),
]:
    r = trace(relay('return nil'), frames)
    assert r['frames'][-1]['last_time_seconds'] == last

# Backend failure must preserve logical state and prior electrical level; retry recovers.
r = trace(relay('return true'), [{'inputs': {}, 'fail_pin': 4}, {'inputs': {}}, {'inputs': {}}])
assert [f['outputs'][0]['value'] for f in r['frames']] == [False, True, True]
assert [f['outputs'][0]['level'] for f in r['frames']] == [True, False, False]
assert r['frames'][0]['outputs'][0]['error'] and r['frames'][1]['outputs'][0]['error'] is None
assert r['errors'] == 1 and r['writes'] == 1
r = trace(relay('while true do end', value=True), [{'inputs': {}}])
assert r['frames'][0]['outputs'][0]['value'] is True and r['errors'] == 1
r = trace(relay('return true', auto=False), [{'inputs': {}}, {'inputs': {}}])
assert r['evaluations'] == 0 and r['writes'] == 0
assert b.get('/api/relays/config')['relays'] == original
assert post('/api/bench/engine-run', {'relays': [relay('return nil')], 'frames': [{}]})[0] == 400
assert post('/api/bench/engine-run', {'relays': [relay('return nil')],
                                    'frames': [{'inputs': {}}] * 17})[0] == 400
print('Shared engine schedules, clock discontinuities, switch edges, output failure/recovery and trace isolation PASS')

try:
    assert post('/api/bench/clock-source', {'source': 'manual'})[0] == 200
    assert post('/api/relays/config', {'relays': [relay('return true')]})[0] == 200
    time.sleep(1)
    assert b.get('/api/relays/config')['relays'][0]['value'] is True
    assert post('/api/relays/control', {'label': 'engine-test', 'state': False})[0] == 200
    time.sleep(1)
    current = b.get('/api/relays/config')['relays'][0]
    assert current['value'] is False and current['auto'] is False
    levels = b.get('/api/engine/status')['electrical_levels']
    assert levels == [{'pin': 4, 'level': True}]
    assert post('/api/relays/control', {'label': 'missing', 'state': True})[0] == 404
    assert post('/api/relays/control', {'label': 'engine-test', 'state': 1})[0] == 400
    # Real SNTP feeds the SAME runtime loop, but never any physical GPIO.
    assert post('/api/time/config', {'timezone': None})[0] == 200
    assert post('/api/bench/clock-source', {'source': 'network'})[0] == 200
    time.sleep(1)
    assert b.get('/api/sensors')['time_seconds'] is None
    assert b.get('/api/time/status')['feeds_simulated_rules'] is True
    assert post('/api/bench/inputs', {'time_seconds': 1})[0] == 400
    assert post('/api/time/config', {'timezone': 'UTC'})[0] == 200
    deadline = time.monotonic() + 65
    while b.get('/api/sensors')['time_seconds'] is None:
        if time.monotonic() > deadline:
            raise TimeoutError('Network clock did not become usable')
        time.sleep(1)
    assert b.get('/api/engine/status')['backend'] == 'memory-only'
    print('Runtime/manual control, physical-level model and gated SNTP integration PASS')
finally:
    post('/api/bench/clock-source', {'source': original_source})
    post('/api/time/config', {'timezone': original_zone})
    restored = post('/api/relays/config', {'relays': original})
    assert restored[0] == 200
    print('Original relay configuration, timezone and clock source restored')
