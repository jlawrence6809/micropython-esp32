#!/usr/bin/env python3
"""On-spare profile/rule tests using deterministic snapshots, never live controllers."""
import argparse
import ast
import json
import time
from pathlib import Path
from usb import Device, DEFAULT_PORT
from prepare_migration import ROOT, translate


def reference(source, inputs):
    # translate() must recognize the reviewed AST before any reference execution.
    _, schedule = translate(source)
    if schedule is None:
        return 1 if source.strip() else -1
    tree = ast.parse(source)
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Name) and n.value.func.id == 'print')]
    functions = {'__builtins__': {}, 'get_switch_state': lambda: inputs['switch_state'],
                 'get_last_switch_state': lambda: inputs['last_switch_state'],
                 'get_time': lambda: inputs['time_seconds'],
                 'get_last_time': lambda: inputs['last_time_seconds'],
                 'time': lambda h, m=0, s=0: h * 3600 + m * 60 + s}
    values = {}
    exec(compile(tree, '<reviewed reference>', 'exec'), functions, values)
    result = values['result']
    return -1 if result is None else int(result)


def scenarios(schedule):
    base = {'switch_state': False, 'last_switch_state': False,
            'time_seconds': 3600, 'last_time_seconds': 3599}
    if not schedule:
        return [('constant', base, None)]
    start, end = schedule['on_seconds'], schedule['off_seconds']
    cases = []
    for label, t, last, switch, previous in [
        ('before-on', start - 1, start - 2, False, False),
        ('at-on', start, start - 1, False, False),
        ('after-on', start + 1, start, False, False),
        ('before-off', end - 1, end - 2, False, False),
        ('at-off', end, end - 1, False, False),
        ('after-off', end + 1, end, False, False),
        ('switch-on', 3600, 3599, True, False),
        ('switch-off', 3600, 3599, False, True),
        ('switch-held', 3600, 3599, True, True),
        ('midnight', 0, 86399, False, False),
        ('forward-jump', end + 1, start - 1, False, False),
        ('backward-jump', start - 1, end + 1, False, False),
        ('switch-on-at-off', end, end - 1, True, False),
        ('switch-off-at-on', start, start - 1, False, True),
    ]:
        cases.append((label, dict(base, time_seconds=t, last_time_seconds=last,
                                  switch_state=switch, last_switch_state=previous), None))
    cases += [('invalid-clock-hold', dict(base, time_seconds=None, last_time_seconds=None), -1),
              ('invalid-clock-switch-on', dict(base, time_seconds=None, last_time_seconds=None,
                                               switch_state=True), 1),
              ('invalid-clock-switch-off', dict(base, time_seconds=None, last_time_seconds=None,
                                                last_switch_state=True), 0),
              ('first-clock-no-catchup', dict(base, time_seconds=end + 1, last_time_seconds=None), -1)]
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', nargs='+', type=Path)
    parser.add_argument('--port', default=DEFAULT_PORT)
    args = parser.parse_args()
    device = Device(args.port)
    original = device.request('GET', '/api/relays/config')['data']['relays']
    checked = 0
    try:
        for folder in args.folders:
            folder = folder.resolve()
            assert folder.is_relative_to(ROOT.resolve()), 'Private profiles only'
            profile = json.loads((folder / 'native-simulation-profile.json').read_text())
            source = json.loads((folder / 'relays-config.json').read_text())['relays']
            assert profile['simulated'] is True
            plan = device.request('POST', '/api/bench/io-plan', json.dumps({
                'relays': profile['relays'], 'sensor_pins': profile['sensor_pins']}))
            assert plan['status'] == 200 and plan['data']['success'] is True, plan
            assert plan['data']['hardware_applied'] is False
            assert plan['data']['switch_active_low'] is True
            assert plan['data']['switch_debounce_ms'] == 40
            assert {x['pin']: x['boot_level'] for x in plan['data']['relay_boot_levels']} == {
                r['pin']: int(r['defaultValue']) ^ int(r['isInverted']) for r in profile['relays']}
            for old, new, migration in zip(source, profile['relays'], profile['translations'], strict=True):
                lua, schedule = translate(old['rule'])
                assert new['rule'] == lua and migration['schedule'] == schedule
                for label, inputs, explicit in scenarios(schedule):
                    expected = reference(old['rule'], inputs) if explicit is None else explicit
                    response = device.request('POST', '/api/bench/evaluate',
                                              json.dumps({'rule': lua, 'inputs': inputs}))
                    assert response['status'] == 200 and response['data']['result'] == expected, (label, response)
                    checked += 1
            assert device.request('GET', '/api/relays/config')['data']['relays'] == original
            result = device.request('POST', '/api/relays/config', json.dumps({'relays': profile['relays']}))
            assert result['status'] == 200, result
            # Actual spare reset checks persistence and boot policy for every relay.
            device.reset()
            current = device.request('GET', '/api/relays/config')['data']['relays']
            assert len(current) == len(profile['relays'])
            for expected, got in zip(profile['relays'], current, strict=True):
                for field in ('pin', 'label', 'isInverted', 'defaultValue', 'defaultAuto', 'rule'):
                    assert got[field] == expected[field], field
                assert got['value'] is expected['defaultValue']
                assert got['auto'] is expected['defaultAuto']
                assert got['last_error'] is None
            print(f'{profile["source_device"]}: simulated profile, rules, persistence and boot defaults PASS')
            assert device.request('POST', '/api/relays/config', json.dumps({'relays': original}))['status'] == 200
        print(f'PASS: {checked} snapshot/reference comparisons; original spare relay configuration restored')
    finally:
        restored = device.request('POST', '/api/relays/config', json.dumps({'relays': original}))
        device.close()
        if restored['status'] != 200:
            raise RuntimeError('Could not restore spare configuration')

if __name__ == '__main__':
    main()
