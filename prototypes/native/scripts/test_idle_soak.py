#!/usr/bin/env python3
"""Read-only idle/burst soak of the disconnected memory-only spare (no resets).

Requests use one attempt and a four-second timeout, deliberately matching the
intermittent failures under investigation. Initial identity verification alone
uses Bench's logged verification retries. No network reconfiguration, mutation,
USB access or upload. The final verification may extend the duration by 40s.
Reports contain only allowlisted diagnostics, never profiles/SSID/IP/labels.
"""
import argparse
import datetime
import json
import math
import os
from pathlib import Path
import socket
import statistics
import time
import urllib.error
from ota import Bench

PATHS = ('/api/ota/status', '/api/status', '/api/wifi/status',
         '/api/watchdog/status', '/api/engine/status', '/api/profile/edit')
STATUS_KEYS = ('uptime_seconds', 'reset_reason', 'free_heap', 'minimum_free_heap',
               'wifi_disconnects', 'rule_evaluations')
WIFI_KEYS = ('sta_connected', 'sta_rssi', 'disconnect_count', 'last_disconnect_reason')
ENGINE_KEYS = ('evaluations', 'automation_writes', 'rule_or_output_errors', 'clock_discontinuities')


def numeric_fields(data, keys):
    return {key: data[key] for key in keys if key in data and type(data[key]) in (int, float, bool) and math.isfinite(data[key])}


def metrics(path, data):
    if path == '/api/status':
        rows = {r['key']: r['value'] for r in data}
        return numeric_fields(rows, STATUS_KEYS)
    if path == '/api/wifi/status':
        return numeric_fields(data, WIFI_KEYS)
    if path == '/api/engine/status':
        return numeric_fields(data, ENGINE_KEYS)
    if path == '/api/watchdog/status':
        result = numeric_fields(data, ('monitor_active', 'timeout_mask', 'previous_watchdog_mask'))
        ages = data.get('observed_progress_age_ms', {})
        if isinstance(ages, dict):
            result['observed_progress_age_ms'] = numeric_fields(ages, ('rules', 'network', 'usb', 'inputs'))
        return result
    return {}  # Do not store profile, boot identifiers, image hashes or other raw metadata.


def check_identity(path, data, initial):
    problems = []
    if path == '/api/ota/status':
        for field in ('boot_id', 'elf_sha256'):
            if data.get(field) != initial[field]:
                problems.append(field + '_changed')
        if data.get('healthy') is not True or data.get('running_state') != 'valid' or data.get('runtime_watchdog_active') is not True:
            problems.append('runtime_not_healthy')
    if path == '/api/profile/edit':
        if data.get('revision') != initial['revision']:
            problems.append('explicit_configuration_changed')
        if data.get('boot_id') != initial['boot_id']:
            problems.append('edit_boot_changed')
    if path == '/api/watchdog/status':
        if data.get('monitor_active') is not True or data.get('fault_injection') is not False or data.get('timeout_mask') != 0:
            problems.append('watchdog_not_normal')
    if path == '/api/engine/status' and data.get('backend') != 'memory-only':
        problems.append('unexpected_backend')
    return problems


def sample(bench, path, initial, elapsed):
    start = time.monotonic()
    result = {'elapsed_s': round(elapsed, 3), 'path': path}
    try:
        data = bench.get(path)  # Single attempt. Never mask a soak failure with retries.
        result['metrics'] = metrics(path, data)
        result['violations'] = check_identity(path, data, initial)
        result['ok'] = not result['violations']
    except urllib.error.HTTPError as error:
        result.update(ok=False, error='HTTPError', http_status=error.code)
        error.close()
    except Exception as error:
        result.update(ok=False, error=type(error).__name__)
    result['latency_s'] = round(time.monotonic() - start, 4)
    return result


def summarize(samples):
    latencies = sorted(r['latency_s'] for r in samples)
    heaps = [r['metrics']['free_heap'] for r in samples if 'free_heap' in r.get('metrics', {})]
    radios = [r['metrics']['sta_rssi'] for r in samples if 'sta_rssi' in r.get('metrics', {})]
    disconnects = [r['metrics']['disconnect_count'] for r in samples if 'disconnect_count' in r.get('metrics', {})]
    summary = {'requests': len(samples), 'failed': sum(not r['ok'] for r in samples),
               'max_latency_s': max(latencies), 'median_latency_s': statistics.median(latencies),
               'p95_latency_s': latencies[int((len(latencies)-1)*.95)]}
    if heaps:
        summary['heap'] = dict(first=heaps[0], last=heaps[-1], minimum=min(heaps), maximum=max(heaps), retained_delta=heaps[-1]-heaps[0])
    if radios:
        summary['rssi'] = dict(minimum=min(radios), maximum=max(radios))
    if disconnects:
        summary['disconnect_delta'] = disconnects[-1]-disconnects[0]
    summary['heap_headroom_ok'] = bool(heaps) and min(heaps) >= 32768 and heaps[-1] >= heaps[0]-16384
    return summary


def write_report(path, report):
    # Never overwrite an earlier run or follow a symlink. No secrets in report.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('host')
    p.add_argument('--seconds', type=int, default=600)
    p.add_argument('--gaps', default='0,1,5,15,30,60', help='Seconds of silence between read bursts')
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--confirm-memory-only-spare', action='store_true')
    a = p.parse_args()
    try:
        gaps = [float(x) for x in a.gaps.split(',')]
        assert 1 <= len(gaps) <= 8 and all(0 <= x <= 120 for x in gaps) and sum(gaps) > 0
    except (ValueError, AssertionError):
        p.error('Use 1..8 gaps, each 0..120 seconds, with a nonzero total')
    if not a.confirm_memory_only_spare or not 5 <= a.seconds <= 3600 or a.report.exists():
        p.error('Require confirmed disconnected spare, 5..3600 seconds and a new report path')
    b = Bench(a.host)
    io = b.get('/api/io/status')
    assert io['gpio_compiled'] is False and io['gpio_active'] is False and io['cleanup_failed'] is False
    assert b.get('/api/bench/io-status')['physical_selftest_ran'] is False
    wd = b.get('/api/watchdog/status')
    assert wd['fault_injection'] is False and wd['monitor_active'] is True
    initial = b.get('/api/profile/edit')
    assert initial['healthy'] is True and initial['running_state'] == 'valid'
    report = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'planned_seconds': a.seconds, 'gaps_seconds': gaps, 'request_timeout_seconds': 4,
              'read_attempts': 1, 'samples': [], 'tcp_probes': []}
    start = time.monotonic()
    burst = 0
    while time.monotonic() - start < a.seconds:
        time.sleep(min(gaps[burst % len(gaps)], max(0, a.seconds - (time.monotonic() - start))))
        if time.monotonic() - start >= a.seconds:
            break
        for path in PATHS:
            if time.monotonic() - start >= a.seconds:
                break
            result = sample(b, path, initial, time.monotonic() - start)
            report['samples'].append(result)
            if not result['ok']:
                print('SOAK failure:', result['path'], result.get('error', result.get('violations')), 'at', result['elapsed_s'], 'seconds', flush=True)
                # A TCP handshake is diagnostic only, never an HTTP retry.
                then = time.monotonic()
                probe = {'elapsed_s': round(then - start, 3)}
                try:
                    with socket.create_connection((a.host, 80), timeout=1):
                        probe['connected'] = True
                except OSError as error:
                    probe.update(connected=False, error=type(error).__name__)
                probe['latency_s'] = round(time.monotonic() - then, 4)
                report['tcp_probes'].append(probe)
        burst += 1
    for path in PATHS:
        report['samples'].append(sample(b, path, initial, time.monotonic() - start))
    try:
        final_io = b.get('/api/io/status')
        report['final_io_ok'] = all(final_io.get(key) is False for key in ('gpio_compiled', 'gpio_active', 'cleanup_failed', 'armed_for_saved_layout'))
    except Exception as error:
        report.update(final_io_ok=False, final_io_error=type(error).__name__)
    samples = report['samples']
    report['elapsed_seconds'] = round(time.monotonic() - start, 2)
    report['summary'] = summarize(samples)
    report['ok'] = report['final_io_ok'] and report['summary']['failed'] == 0 and report['summary']['heap_headroom_ok']
    write_report(a.report, report)
    print('Idle/burst soak:', json.dumps(report['summary']), 'final_io_ok=', report['final_io_ok'], flush=True)
    print('No reset, upload, profile/input mutation or Wi-Fi reconfiguration issued. Short success is not long-term proof.')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
