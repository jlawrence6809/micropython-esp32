#!/usr/bin/env python3
"""Bench-only USB provisioning and API regression tests. Requires pyserial."""
import argparse
import copy
import getpass
import json
import os
import time
import serial
import sys


def prevent_linux_hangup_reset(port):
    """Keep this maintenance TTY's modem lines stable on close (CH340 reset/BOOT).

    Per-device transient termios state only, reset on unplug; no udev/global policy.
    Opening the adapter may still reset hardware and needs maintenance approval.
    """
    if sys.platform.startswith('linux'):
        import termios
        attrs = termios.tcgetattr(port.fileno())
        if attrs[2] & termios.HUPCL:
            attrs[2] &= ~termios.HUPCL
            termios.tcsetattr(port.fileno(), termios.TCSANOW, attrs)


# Device-specific paths belong in private configuration, not source defaults.
DEFAULT_PORT = os.environ.get('GARDEN_BENCH_PORT')

class Device:
    def __init__(self, port, controller=False):
        if not isinstance(port, str) or not port:
            raise ValueError('Explicit --port or GARDEN_BENCH_PORT required; no automatic device selection')
        self.serial = serial.Serial(port=None, baudrate=115200, timeout=0.25, write_timeout=8)
        self.serial.dtr = False
        self.serial.rts = False
        self.serial.port = port
        self.serial.open()
        try:
            prevent_linux_hangup_reset(self.serial)
        except Exception:
            self.serial.close()
            raise
        self.sequence = 0
        # Opening a USB adapter can coincide with boot or incomplete RX bytes.
        # Retry ONLY this read-only identity query, never mutation requests.
        time.sleep(0.5)
        for attempt in range(3):
            try:
                reply = self.request('GET', '/api/config')
                cfg = reply['data']
                role = cfg.get('device_role')
                allowed = role == 'relay-controller' if controller else (
                    cfg.get('simulated') is True and (role == 'development-bench' or
                    (not role and cfg.get('hostname') == 'garden-bench')))
                if reply['status'] == 200 and allowed:
                    break
            except TimeoutError:
                pass
            if attempt == 2:
                self.serial.close()
                raise RuntimeError('No device with the explicitly requested role on this USB port')
            time.sleep(1)
        self.wait_healthy()

    def wait_healthy(self):
        # Read-only polling; do not replay mutation requests after uncertain replies.
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            status = self.request('GET', '/api/ota/status')['data']
            if status.get('healthy') and status.get('running_state') == 'valid':
                return
            time.sleep(0.25)
        raise TimeoutError('Bench boot not locally validated')

    def command(self, obj):
        self.sequence += 1
        obj = dict(obj, id=self.sequence)
        wire = json.dumps(obj, separators=(',', ':')).encode() + b'\n'
        if len(wire) > 12288:
            raise ValueError('USB request too large')
        self.serial.reset_input_buffer()
        # A USB bulk endpoint can apply backpressure indefinitely if firmware
        # does not drain RX. Bound the write as well as the reply-read deadline.
        # Failure is uncertain for mutations: caller must inspect, never replay.
        self.serial.write_timeout = 8
        self.serial.write(wire)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            line = self.serial.readline()
            marker = b'USB_RESPONSE '
            if marker in line:
                reply = json.loads(line.split(marker, 1)[1])
                if reply.get('id') == self.sequence:
                    return reply
        raise TimeoutError('No USB response (request content deliberately not logged)')

    def request(self, method, path, body=''):
        return self.command({'op': 'request', 'method': method, 'path': path, 'body': body})

    def reset(self, wait_healthy=True):
        self.serial.reset_input_buffer()
        self.serial.rts = True
        time.sleep(0.1)
        self.serial.rts = False
        deadline = time.monotonic() + 15
        boot = bytearray()
        while time.monotonic() < deadline:
            boot.extend(self.serial.read(4096))
            if b'RUNTIME_READY ' in boot:
                assert b'BENCH_PASS ' in boot and b' FAIL ' not in boot
                if wait_healthy:
                    self.wait_healthy()
                return
        raise TimeoutError('Bench failed to become ready after reset')

    def close(self):
        self.serial.close()


def test(device):
    cfg = device.request('GET', '/api/config')
    assert cfg['status'] == 200 and cfg['data']['simulated'] is True
    wifi_before = device.request('GET', '/api/wifi/status')['data']['provisioned']
    assert device.command({'op': 'provision', 'ssid': '', 'password': ''})['status'] == 400
    assert device.request('GET', '/api/wifi/status')['data']['provisioned'] == wifi_before
    original = device.request('GET', '/api/relays/config')['data']['relays']
    assert device.request('GET', '/api/sensors')['data']['temperature'] == 23
    assert isinstance(device.request('GET', '/api/status')['data'], list)
    for rule, success in [('return true', True), ('return false', True), ('return nil', True),
                          ('while true do end', False), ('return (', False),
                          ('return os.execute("x")', False), ('return 1', False),
                          ('x' * 2049, False)]:
        result = device.request('POST', '/api/validate-rule', rule)
        assert result['status'] == 200 and result['data']['success'] is success, result
    # Validation must not mutate outputs.
    assert device.request('GET', '/api/relays/config')['data']['relays'] == original
    trial = [{'pin': 1, 'label': 'TEST simulated', 'rule': 'return true', 'value': False,
              'auto': True, 'isInverted': False, 'defaultValue': False, 'defaultAuto': False}]
    try:
        assert device.request('POST', '/api/relays/config', '{')['status'] == 400
        assert device.request('POST', '/api/relays/config', '[' * 30 + ']' * 30)['status'] == 400
        invalid = copy.deepcopy(trial)
        invalid[0]['pin'] = 43  # UART/USB-console pin is outside allowed simulation identifiers
        assert device.request('POST', '/api/relays/config', json.dumps({'relays': invalid}))['status'] == 400
        duplicate = trial + copy.deepcopy(trial)
        assert device.request('POST', '/api/relays/config', json.dumps({'relays': duplicate}))['status'] == 400
        assert device.request('POST', '/api/relays/config', json.dumps({'relays': trial}))['status'] == 200
        time.sleep(1)
        r = device.request('GET', '/api/relays/config')['data']['relays'][0]
        assert r['value'] is True and r['last_error'] is None
        r['rule'] = 'while true do end'
        assert device.request('POST', '/api/relays/config', json.dumps({'relays': [r]}))['status'] == 200
        time.sleep(1)
        r = device.request('GET', '/api/relays/config')['data']['relays'][0]
        assert r['value'] is True and 'budget' in r['last_error']
        r['rule'] = 'return false'
        assert device.request('POST', '/api/relays/config', json.dumps({'relays': [r]}))['status'] == 200
        time.sleep(1)
        r = device.request('GET', '/api/relays/config')['data']['relays'][0]
        assert r['value'] is False and r['last_error'] is None
        assert device.request('GET', '/api/not-implemented')['status'] == 404
        r.update(rule='return nil', value=False, auto=True, defaultValue=True, defaultAuto=False)
        assert device.request('POST', '/api/relays/config', json.dumps({'relays': [r]}))['status'] == 200
        device.reset()
        r = device.request('GET', '/api/relays/config')['data']['relays'][0]
        assert r['label'] == 'TEST simulated' and r['value'] is True and r['auto'] is False
        # Reboot also reconnects Wi-Fi; do not mistake connection-time allocations
        # for a rule-interpreter leak. Wait for configured networking to settle.
        for _ in range(45):
            wifi = device.request('GET', '/api/wifi/status')['data']
            if not wifi['provisioned'] or wifi['sta_connected']:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Provisioned Wi-Fi did not reconnect after bench reset')
        time.sleep(3)
        def heap():
            return next(row['value'] for row in device.request('GET', '/api/status')['data'] if row['key'] == 'free_heap')
        # Warm up then check that repeated interpreter creation is not steadily leaking.
        for _ in range(10):
            assert device.request('POST', '/api/validate-rule', 'return nil')['data']['success']
        before = heap()
        for _ in range(200):
            assert device.request('POST', '/api/validate-rule', 'return nil')['data']['success']
        after = heap()
        # Wi-Fi/mDNS may allocate concurrently; allow a small bounded fluctuation.
        assert after >= before - 4096, (before, after)
        print(f'PASS: API dispatch, input rejection, validation isolation, automation, error recovery, reboot persistence/boot defaults; 200 evaluations heap {before}->{after}')
    finally:
        restored = device.request('POST', '/api/relays/config', json.dumps({'relays': original}))
        if restored['status'] != 200:
            raise RuntimeError('Failed to restore bench relay configuration')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['provision', 'status', 'test'])
    parser.add_argument('--port', default=DEFAULT_PORT)
    args = parser.parse_args()
    device = Device(args.port)
    try:
        if args.action == 'provision':
            ssid = input('Wi-Fi SSID (2.4 GHz): ')
            password = getpass.getpass('Wi-Fi password (hidden; empty for open network): ')
            reply = device.command({'op': 'provision', 'ssid': ssid, 'password': password})
            del password
            print(json.dumps(reply))
            if reply['status'] != 200:
                raise RuntimeError('Provisioning failed')
            print('Waiting up to 45 seconds for an IP...')
            for _ in range(45):
                time.sleep(1)
                status = device.request('GET', '/api/wifi/status')['data']
                if status.get('sta_connected'):
                    print(json.dumps(status, indent=2))
                    return
            print('Not connected yet; credentials saved. Use status to inspect diagnostics.')
        elif args.action == 'test':
            test(device)
        else:
            for path in ('/api/config', '/api/wifi/status', '/api/status', '/api/relays/config'):
                print(path, json.dumps(device.request('GET', path)['data'], indent=2))
    finally:
        device.close()

if __name__ == '__main__':
    main()
