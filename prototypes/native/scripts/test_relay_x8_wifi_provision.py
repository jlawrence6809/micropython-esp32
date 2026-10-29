#!/usr/bin/env python3
"""Offline fake-UART/HTTP Wi-Fi provision/no-replay regressions. No credentials."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlparse
import remote_relay_x8_wifi_provision as worker
from test_controller_release import snapshot

class Tests(unittest.TestCase):
    def setUp(self):
        self.s=snapshot(False);self.s['config']['chip_target']='esp32'
        self.s['ota'].update(chip_target='esp32',image_chip_id=0,update_partition_bytes=0x180000)
        self.profile=json.loads((Path(__file__).resolve().parents[1]/'profiles/relay_x8_unarmed.json').read_text())
        self.c=dict(purpose='relay-x8-private-wifi-provision',apply_confirmed=True,loads_disconnected=True,port='/fake',
                    approved_ssid='test-network',wifi=dict(ssid='test-network',password='fake-test-password'),expected_device_id='123456abcdef',
                    expected_boot_id='b'*16,expected_revision='d'*64,expected_profile=self.profile,
                    expected_image=dict(chip_target='esp32',image_chip_id=0,bytes=1024,elf_sha256='a'*64))
        self.provisions=0;self.provisioned=False;self.closed=False;self.log=io.StringIO();self.lan_calls=[]
    def invoke(self,mode='ok'):
        outer=self;routes=dict(zip(['/api/config','/api/io/status','/api/ota/status','/api/watchdog/status','/api/profile/edit','/api/ota/fence'],['config','io','ota','watchdog','edit','fence']))
        def get(route):
            if route in routes:return copy.deepcopy(outer.s[routes[route]])
            if route=='/api/profile':return copy.deepcopy(outer.profile)
            if route=='/api/status':return []
            if route=='/api/wifi/status':return dict(provisioned=outer.provisioned,sta_connected=outer.provisioned,
                sta_ssid='test-network',sta_ip='8.8.8.8' if mode=='public_ip' else '192.168.0.123')
            raise AssertionError('Unexpected route')
        class Port:
            def __init__(self,**kw):pass
            def open(self):pass
            def close(self):outer.closed=True
        class Device:
            def request(self,method,route):
                outer.assertEqual(method,'GET');return dict(status=200,data=get(route))
            def command(self,obj):
                outer.assertEqual(set(obj),{'op','ssid','password'});outer.assertEqual(obj['op'],'provision')
                outer.provisions+=1;outer.provisioned=True
                if mode=='lost_reply':raise TimeoutError('Uncertain after save')
                return dict(status=400 if mode=='reject' else 200,data=dict(success=mode!='reject'))
        class Opener:
            def open(self,url,timeout):
                outer.lan_calls.append(url)
                if mode=='lan_timeout':raise TimeoutError('LAN unavailable')
                return io.BytesIO(json.dumps(get(urlparse(url).path)).encode())
        tick=iter(range(1000))
        with patch.dict(sys.modules,serial=types.SimpleNamespace(Serial=Port),
             usb=types.SimpleNamespace(Device=Device,prevent_linux_hangup_reset=lambda p:None)), \
             patch.object(worker,'guard_port',lambda c:contextlib.nullcontext()), \
             patch.object(worker.urllib.request,'build_opener',return_value=Opener()), \
             patch.object(worker.time,'sleep',lambda _:None),patch.object(worker.time,'monotonic',lambda:next(tick)), \
             patch.object(sys,'__stdout__',self.log):worker.run(self.c)
    def test_success_once_and_get_only_lan(self):
        self.invoke();self.assertEqual(self.provisions,1);self.assertTrue(self.closed)
        events=[json.loads(x) for x in self.log.getvalue().splitlines()]
        self.assertEqual(sum(x['stage']=='lan_sample' for x in events),8)
        self.assertEqual(events[-1]['stage'],'wifi_bench_passed')
        self.assertNotIn('fake-test-password',self.log.getvalue())
    def test_wrong_identity_no_provision(self):
        self.c['expected_device_id']='0'*12
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.provisions,0)
    def test_existing_credentials_no_replay(self):
        self.provisioned=True
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.provisions,0)
    def test_lost_reply_never_replays(self):
        with self.assertRaises(TimeoutError):self.invoke('lost_reply')
        self.assertEqual(self.provisions,1);self.assertTrue(self.closed);self.assertFalse(self.lan_calls)
    def test_reject_never_replays(self):
        with self.assertRaises(ValueError):self.invoke('reject')
        self.assertEqual(self.provisions,1);self.assertTrue(self.closed)
    def test_lan_failure_never_reprovisions(self):
        with self.assertRaises(TimeoutError):self.invoke('lan_timeout')
        self.assertEqual(self.provisions,1);self.assertEqual(len(self.lan_calls),1)
    def test_nonprivate_ip_blocks_http(self):
        with self.assertRaises(ValueError):self.invoke('public_ip')
        self.assertEqual(self.provisions,1);self.assertFalse(self.lan_calls)
    def test_missing_network_approval_rejected(self):
        del self.c['approved_ssid']
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_network_not_approved(self):
        self.c['wifi']['ssid']='other'
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_redirect_disabled(self):self.assertIsNone(worker.NoRedirect().redirect_request(None))

if __name__=='__main__':unittest.main()
