#!/usr/bin/env python3
"""Read-only/validation HTTP smoke checks, restricted to a simulated bench device."""
import argparse
import json
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('host', help='Spare board IP or garden-bench.local, without http://')
args = parser.parse_args()
if any(ch in args.host for ch in '/@?#'):
    parser.error('Use a hostname or IP, not a URL')
base = 'http://' + args.host
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def request(path, body=None):
    req = urllib.request.Request(base + path, data=body.encode() if body is not None else None,
                                 headers={'Content-Type': 'text/plain'})
    try:
        with opener.open(req, timeout=8) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

status, cfg = request('/api/config')
assert status == 200 and cfg.get('simulated') is True, 'Not a simulated bench device; stopping'
_, before = request('/api/relays/config')
assert request('/api/sensors')[1]['simulated'] is True
assert request('/api/wifi/status')[1]['sta_connected'] is True
assert isinstance(request('/api/status')[1], list)
for source, expected in [('return true', True), ('return nil', True),
                         ('while true do end', False), ('return (', False)]:
    status, response = request('/api/validate-rule', source)
    assert status == 200 and response['success'] is expected
# Must not actuate or change relay configuration during validation.
_, after = request('/api/relays/config')
assert before == after, 'Relay state changed (could also be active automation; test with auto disabled)'
assert request('/api/validate-rule', 'x' * 13000)[0] == 413
assert request('/api/not-implemented')[0] == 404
print('PASS: HTTP identity, diagnostics, validation, output isolation and oversized-input handling')
