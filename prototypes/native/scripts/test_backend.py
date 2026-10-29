#!/usr/bin/env python3
"""Software-only backend/arming guard regression; never installs controller firmware."""
import argparse
import copy
import json
import urllib.request
from unittest import mock
from ota import Bench
from usb import Device, DEFAULT_PORT

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('host')
p.add_argument('--port',default=DEFAULT_PORT)
a=p.parse_args()

# An unarmed controller may say simulated=true, but bench tools must still refuse it.
for cfg, allowed in [
    ({'simulated':True,'device_role':'development-bench','hostname':'renamed'},True),
    ({'simulated':True,'hostname':'garden-bench'},True),
    ({'simulated':True,'device_role':'relay-controller','hostname':'garden-bench'},False),
    ({'simulated':False,'device_role':'development-bench','hostname':'garden-bench'},False),
    ({'simulated':True,'device_role':'unknown','hostname':'garden-bench'},False),
]:
    with mock.patch.object(Bench,'get',return_value=cfg):
        try:
            Bench('127.0.0.1')
        except RuntimeError:
            assert not allowed
        else:
            assert allowed
    with mock.patch('usb.serial.Serial'), mock.patch('usb.time.sleep'), \
         mock.patch.object(Device,'request',return_value={'status':200,'data':cfg}), \
         mock.patch.object(Device,'wait_healthy'):
        try:
            d=Device('unused')
        except RuntimeError:
            assert not allowed
        else:
            assert allowed
            d.close()
print('HTTP/USB role separation including unarmed controller refusal PASS')

b=Bench(a.host)
d=Device(a.port)
try:
    assert d.request('GET','/api/ota/status')['data']['boot_id']==b.get('/api/ota/status')['boot_id']
    original=b.get('/api/profile')
    io=b.get('/api/io/status')
    assert io['gpio_compiled'] is False and io['gpio_active'] is False
    assert io['backend_software_tests_passed'] is True and io['cleanup_failed'] is False
    assert d.request('POST','/api/bench/backend-selftest','{}')['data']['success'] is True
    for op in ('io_arm','io_disarm'):
        result=d.command({'op':op,'layout_hash':io['layout_hash'],'device_id':io['device_id'],
                          'confirm':('enable' if op=='io_arm' else 'disable')+' relay outputs after reboot'})
        assert result['status']==400
    assert d.request('POST','/api/io/arm','{}')['status']==404
    base=copy.deepcopy(original)
    base['relays']=[{'pin':4,'label':'layout test','rule':'return nil','value':False,'auto':False,
                     'isInverted':True,'defaultValue':False,'defaultAuto':False}]
    base['sensor_pins']={key:-1 for key in base['sensor_pins']}
    base['sensor_pins']['light_switch']=5
    base.update(timezone='UTC',clock_source='network')

    def fingerprint(value):
        reply=d.request('POST','/api/profile/validate',json.dumps(value))
        assert reply['status']==200, reply['status']
        return reply['data']['layout_hash']

    expected=fingerprint(base)
    for key,value in [('value',True),('auto',True),('label','renamed'),('rule','return true')]:
        item=copy.deepcopy(base);item['relays'][0][key]=value
        assert fingerprint(item)==expected
    item=copy.deepcopy(base);item['hostname']='renamed';assert fingerprint(item)==expected
    item=copy.deepcopy(base);item['sensor_pins']=dict(reversed(list(item['sensor_pins'].items())))
    assert fingerprint(item)==expected
    for key,value in [('pin',6),('isInverted',False),('defaultValue',True),('defaultAuto',True)]:
        item=copy.deepcopy(base);item['relays'][0][key]=value
        assert fingerprint(item)!=expected
    for key,value in [('timezone',None),('clock_source','manual')]:
        item=copy.deepcopy(base);item[key]=value
        assert fingerprint(item)!=expected
    item=copy.deepcopy(base);item['sensor_pins']['light_switch']=13
    assert fingerprint(item)!=expected
    assert b.get('/api/profile')==original
    assert b.get('/api/io/status')['armed_for_saved_layout'] is False
    print('Resource lifecycle/partial-init/write/cleanup failures, layout binding and all activation guards PASS; no GPIO/settings applied')
finally:
    d.close()
