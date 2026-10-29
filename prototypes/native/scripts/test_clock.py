#!/usr/bin/env python3
"""Clock diagnostics/settings tests on the simulated spare; restores timezone."""
import argparse
import datetime
import json
import time
import urllib.request
from zoneinfo import ZoneInfo
from ota import Bench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('host')
parser.add_argument('--reset-port', help='Optional verified spare USB port for timezone persistence test')
args = parser.parse_args()
bench = Bench(args.host)
original = bench.get('/api/time/status')['timezone']
original_source = bench.get('/api/engine/status')['clock_source']

def configure(zone):
    req = urllib.request.Request(bench.base + '/api/time/config',
                                 data=json.dumps({'timezone': zone}).encode(),
                                 headers={'Content-Type': 'application/json'})
    with bench.opener.open(req, timeout=5) as response:
        assert json.load(response)['success'] is True

def set_source(source):
    req = urllib.request.Request(bench.base + '/api/bench/clock-source',
                                 data=json.dumps({'source': source}).encode(),
                                 headers={'Content-Type': 'application/json'})
    with bench.opener.open(req, timeout=5) as response:
        assert json.load(response)['success'] is True

try:
    if original_source != 'manual':
        set_source('manual')
    for zone in ('UTC', 'America/Los_Angeles', 'America/New_York'):
        configure(zone)
        deadline = time.monotonic() + 65
        while True:
            status = bench.get('/api/time/status')
            if status['synchronized']:
                break
            if time.monotonic() > deadline:
                raise TimeoutError('SNTP sync not observed; no assumption that device clock is valid')
            time.sleep(1)
        expected = datetime.datetime.fromtimestamp(status['unix_seconds'], ZoneInfo(zone))
        assert abs(status['unix_seconds'] - time.time()) <= 5
        assert status['local'] == expected.strftime('%Y-%m-%dT%H:%M:%S')
        assert status['is_dst'] is bool(expected.dst())
        assert status['schedule_clock_valid'] is True and status['feeds_simulated_rules'] is False
        assert bench.get('/api/sensors')['time_seconds'] is None
        # Pure conversions across both US spring-forward/fall-back boundaries.
        # This does not change the board's UTC clock or simulated inputs.
        for fixture in ('2026-03-08T06:59:59Z', '2026-03-08T07:00:00Z',
                        '2026-03-08T09:59:59Z', '2026-03-08T10:00:00Z',
                        '2026-11-01T05:59:59Z', '2026-11-01T06:00:00Z',
                        '2026-11-01T08:59:59Z', '2026-11-01T09:00:00Z'):
            epoch = int(datetime.datetime.fromisoformat(fixture).timestamp())
            req = urllib.request.Request(bench.base + '/api/bench/local-time',
                                         data=json.dumps({'unix_seconds': epoch}).encode(),
                                         headers={'Content-Type': 'application/json'})
            with bench.opener.open(req, timeout=5) as response:
                converted = json.load(response)
            expected = datetime.datetime.fromtimestamp(epoch, ZoneInfo(zone))
            assert converted['local'] == expected.strftime('%Y-%m-%dT%H:%M:%S')
            assert converted['is_dst'] is bool(expected.dst())
            assert converted['local_seconds'] == expected.hour * 3600 + expected.minute * 60 + expected.second
    if args.reset_port:
        from usb import Device
        configure('UTC')
        device = Device(args.reset_port)
        try:
            device.reset()
        finally:
            device.close()
        bench.wait(lambda s: s['healthy'] and s['running_state'] == 'valid')
        assert bench.get('/api/time/status')['timezone'] == 'UTC'
        print('Timezone persistence across spare reset PASS')
    configure(None)
    status = bench.get('/api/time/status')
    assert status['timezone'] is None and status['schedule_clock_valid'] is False
    print('SNTP/UTC/local time, 24 DST boundary conversions and unconfirmed-timezone gating PASS')
finally:
    configure(original)
    if original_source != 'manual':
        set_source(original_source)
    print('Original timezone and clock source restored')
