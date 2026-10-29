#!/usr/bin/env python3
"""Prepare private simulation profiles. Recognizes ONLY reviewed rule ASTs; fails closed."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/var/lib/private-services/agent-state/jeremy/garden-device-backups')


def canonical(source):
    tree = ast.parse(source)
    # Strip standalone diagnostic print calls, never execute source code.
    tree.body = [node for node in tree.body if not (isinstance(node, ast.Expr)
                 and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                 and node.value.func.id == 'print')]
    return ast.dump(tree, include_attributes=False)

COMMON = '''switch_edge_on = get_switch_state() and not get_last_switch_state()
switch_edge_off = not get_switch_state() and get_last_switch_state()
t = get_time()
last_t = get_last_time()
'''
KNOWN = {
    canonical(COMMON + '''crossed_2pm = last_t < time(14, 0) <= t
crossed_10pm = last_t < time(22, 0) <= t
result = True if (switch_edge_on or crossed_2pm) else (False if (switch_edge_off or crossed_10pm) else None)
'''): (14, 22),
    canonical(COMMON + '''off_time = time(22, 0)
crossed_2pm = last_t < time(9, 0) <= t
crossed_10pm = last_t < off_time <= t
result = True if (switch_edge_on or crossed_2pm) else (False if (switch_edge_off or crossed_10pm) else None)
'''): (9, 22),
    canonical(COMMON + '''on_time = time(8, 0)
off_time = time(21, 0)
crossed_on = last_t < on_time <= t
crossed_off = last_t < off_time <= t
result = True if (switch_edge_on or crossed_on) else (False if (switch_edge_off or crossed_off) else None)
'''): (8, 21),
}


def translate(source):
    normalized = canonical(source)
    if normalized == canonical('True'):
        return 'return true', None
    if not source.strip():
        return '', None
    if normalized not in KNOWN:
        raise ValueError('Unreviewed automation rule; refusing automatic translation')
    start, end = KNOWN[normalized]
    lua = f'''local switch_on = get_switch_state() and not get_last_switch_state()
local switch_off = not get_switch_state() and get_last_switch_state()
local t, previous = get_time(), get_last_time()
local crossed_on, crossed_off = false, false
if t ~= nil and previous ~= nil then
    crossed_on = previous < time({start}, 0) and time({start}, 0) <= t
    crossed_off = previous < time({end}, 0) and time({end}, 0) <= t
end
if switch_on or crossed_on then return true end
if switch_off or crossed_off then return false end
return nil'''
    return lua, {'on_seconds': start * 3600, 'off_seconds': end * 3600}


def prepare(folder):
    folder = folder.resolve()
    if not folder.is_relative_to(ROOT.resolve()):
        raise ValueError('Profiles must remain within the private backup vault')
    manifest = json.loads((folder / 'manifest.json').read_text())
    for name, checksum in manifest['files'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != checksum:
            raise ValueError('Backup checksum mismatch')
    relays = json.loads((folder / 'relays-config.json').read_text())['relays']
    prepared, translations = [], []
    for r in relays:
        lua, schedule = translate(r['rule'])
        item = {key: r[key] for key in ('pin', 'label', 'isInverted', 'defaultValue', 'defaultAuto')}
        item.update(rule=lua, value=r['defaultValue'], auto=r['defaultAuto'])
        prepared.append(item)
        translations.append({'pin': r['pin'], 'label': r['label'], 'schedule': schedule,
                             'source_sha256': hashlib.sha256(r['rule'].encode()).hexdigest()})
    profile = {'simulated': True, 'source_device': manifest['device'],
               'relays': prepared, 'translations': translations,
               'source_identity': json.loads((folder / 'config.json').read_text()),
               'sensor_pins': json.loads((folder / 'sensor-config.json').read_text())['sensor_pins'],
               'observed_time': [r for r in json.loads((folder / 'status.json').read_text())
                                 if r['key'] in ('Current Time', 'Current Date', 'Timezone')],
               'clock_policy': 'Unconfirmed timezone/DST; simulated timestamps only. No schedule catch-up on boot or invalid clock.',
               'limitations': ['Diagnostic print statements removed; reviewed logic preserved',
                               'Boot defaults used instead of momentary output/auto state',
                               'Sensor pins recorded only; native physical drivers not implemented',
                               'Simulation only; not a production provisioning file']}
    (folder / 'native-simulation-profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    print(f'{manifest["device"]}: prepared {len(prepared)} simulated relays, {sum(bool(t["schedule"]) for t in translations)} scheduled rules')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', nargs='+', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    for folder in args.folders:
        prepare(folder)
