#!/usr/bin/env python3
"""Atomic partial-update tests on verified memory-only spare. No physical GPIO."""
import argparse
import json
import time
import urllib.error
import urllib.request
from ota import Bench

p=argparse.ArgumentParser(description=__doc__);p.add_argument('host');a=p.parse_args()
b=Bench(a.host)
assert not b.get('/api/io/status')['gpio_compiled']
assert not b.get('/api/watchdog/status')['fault_injection']
start=b.wait(lambda s:s['healthy'] and s['running_state']=='valid')
original=b.get('/api/profile');original_switch=b.get('/api/sensors')['switch_state']

def post(path,body):
    raw=body.encode() if isinstance(body,str) else json.dumps(body).encode()
    req=urllib.request.Request(b.base+path,data=raw,headers={'Content-Type':'application/json'})
    try:
        with b.opener.open(req,timeout=12) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)

def patch(changes,snapshot=None):
    s=snapshot or b.get('/api/profile/edit')
    return post('/api/profile/patch',{'expected_revision':s['revision'],'expected_boot_id':s['boot_id'],'changes':changes})

def wait_value(label,value):
    end=time.monotonic()+5
    while time.monotonic()<end:
        r=next(r for r in b.get('/api/relays/config')['relays'] if r['label']==label)
        if r['value'] is value:return
        time.sleep(.1)
    raise AssertionError('Automation fixture did not reach requested RAM state')

try:
    bad=[{}, {'armed':True}, {'relays':[]}, {'sensor_pins':{'light_switch':True}},
         {'sensor_pins':{'ds18b20':3}}, {'timezone':'Mars'}, {'clock_source':'bad'},
         {'relay_update':{'pin':original['relays'][0]['pin'],'label':original['relays'][0]['label'],'changes':{'value':True}}},
         {'relay_update':{'pin':original['relays'][0]['pin'],'label':'missing','changes':{'auto':True}}}]
    for changes in bad:
        before=b.get('/api/profile/edit')
        assert patch(changes,before)[0]==400
        assert b.get('/api/profile/edit')['revision']==before['revision']
    s=b.get('/api/profile/edit')
    duplicate='{"expected_revision":"'+s['revision']+'","expected_boot_id":"'+s['boot_id']+'","changes":{"hostname":"one","hostname":"two"}}'
    assert post('/api/profile/patch',duplicate)[0]==400
    assert b.get('/api/profile/edit')['revision']==s['revision']
    assert patch({'hostname':'atomic-edit-bench'},s)[0]==200
    assert patch({'hostname':'stale-overwrite'},s)[0]==409
    fresh=b.get('/api/profile/edit')
    fresh['boot_id']='0'*16
    assert patch({'hostname':'wrong-boot'},fresh)[0]==409
    assert b.get('/api/profile')['hostname']=='atomic-edit-bench'
    assert patch({'hostname':original['hostname']})[0]==200

    used={r['pin'] for r in original['relays']}|set(original['sensor_pins'].values())
    free=[int(k) for k in b.get('/api/gpio/available') if int(k) not in used]
    assert free
    label='atomic-edit-fixture';pin=free[0]
    assert post('/api/bench/inputs',{'switch_state':False})[0]==200
    add={'pin':pin,'label':label,'rule':'return get_switch_state()','isInverted':False,'defaultValue':False,'defaultAuto':True}
    assert patch({'relay_add':add})[0]==200
    wait_value(label,False)
    snapshot=b.get('/api/profile/edit')
    assert post('/api/bench/inputs',{'switch_state':True})[0]==200
    wait_value(label,True)
    assert b.get('/api/profile/edit')['revision']==snapshot['revision']
    renamed=label+'-new'
    assert patch({'relay_update':{'pin':pin,'label':label,'changes':{'label':renamed}}},snapshot)[0]==200
    wait_value(renamed,True)
    # Explicit user writes must invalidate edits even if resulting config/auto
    # looks identical; automation changes alone deliberately do not.
    stale=b.get('/api/profile/edit')
    assert post('/api/relays/control',{'label':renamed,'state':False})[0]==200
    assert patch({'relay_update':{'pin':pin,'label':renamed,'changes':{'auto':True}}},stale)[0]==409
    stale=b.get('/api/profile/edit')
    assert post('/api/relays/control',{'label':renamed,'state':False})[0]==200
    assert b.get('/api/profile/edit')['revision']!=stale['revision']  # Same state/AUTO; explicit-write generation still changes.
    assert patch({'relay_update':{'pin':pin,'label':renamed,'changes':{'auto':True}}},stale)[0]==409
    assert patch({'relay_update':{'pin':pin,'label':renamed,'changes':{'rule':'return nil','auto':True}}})[0]==200
    wait_value(renamed,False)
    assert patch({'relay_remove':{'pin':pin,'label':renamed}})[0]==200
    assert patch({'sensor_pins':{'light_switch':pin}})[0]==200
    assert b.get('/api/profile')['sensor_pins']['light_switch']==pin
    assert patch({'sensor_pins':{'light_switch':original['sensor_pins']['light_switch']}})[0]==200
    print('Atomic edits PASS: strict rejection, stale/reboot conflicts, runtime-value preservation, manual invalidation, AUTO/rule/add/remove/input updates')
finally:
    current=b.get('/api/ota/status')
    assert current['boot_id']==start['boot_id'] and current['elf_sha256']==start['elf_sha256'], 'Inspect changed firmware/boot before restoring'
    assert not b.get('/api/io/status')['gpio_compiled']
    assert post('/api/bench/inputs',{'switch_state':original_switch})[0]==200
    code,result=post('/api/profile/import',original)
    assert code==200 and result['success'], 'Restoration unconfirmed; inspect before another write'
    assert b.get('/api/profile')==original
    print('Original full profile/input restored on same healthy memory-only boot')
