#!/usr/bin/env python3
"""Offline fake-UART tests for one-shot unloaded all-OFF arming. No hardware."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch
from test_controller_release import snapshot
import remote_relay_x8_arm as worker

class Tests(unittest.TestCase):
    def setUp(self):
        p=json.loads((Path(__file__).resolve().parents[1]/'profiles/relay_x8_unarmed.json').read_text())
        p.update(clock_source='network',timezone='America/Los_Angeles')
        self.c=dict(purpose='relay-x8-attended-unloaded-arm',apply_confirmed=True,loads_disconnected=True,operator_present=True,
                    gpio_enable_authorized=True,profile=p,image=dict(chip_target='esp32',image_chip_id=0,bytes=964640,elf_sha256='a'*64),
                    port='/fake',expected_device_id='123456abcdef',expected_boot_id='b'*16,expected_layout_hash='c'*64,expected_revision='d'*64)
        self.s=snapshot(False);self.s['edit']['profile']=copy.deepcopy(p)
        self.s['config'].update(chip_target='esp32',hostname='relay-x8-bench',active_hostname='relay-x8-bench')
        self.s['ota'].update(chip_target='esp32',image_chip_id=0,update_partition_bytes=0x180000)
        self.s['clock']=dict(timezone='America/Los_Angeles',timezone_confirmed=True,synchronized=True,schedule_clock_valid=True,unix_seconds=time.time())
        self.calls=[];self.closed=False;self.log=io.StringIO()
    def invoke(self,lost_reply=False):
        outer=self;routes={'/api/config':'config','/api/io/status':'io','/api/ota/status':'ota','/api/watchdog/status':'watchdog',
                           '/api/profile/edit':'edit','/api/ota/fence':'fence','/api/time/status':'clock'}
        class Port:
            def __init__(self,**kw):pass
            def open(self):pass
            def close(self):outer.closed=True
        class Device:
            def request(self,method,route):
                outer.assertEqual(method,'GET')
                data=outer.s['edit']['profile'] if route=='/api/profile' else outer.s[routes[route]]
                return dict(status=200,data=copy.deepcopy(data))
            def command(self,obj):
                outer.calls.append(obj);outer.assertEqual(obj,dict(op='io_arm',device_id='123456abcdef',layout_hash='c'*64,
                    boot_id='b'*16,confirm='enable relay outputs after reboot'))
                outer.s['io']['armed_for_saved_layout']=True
                if lost_reply:raise TimeoutError('Saved but reply lost')
                return dict(status=200,data=dict(success=True))
        with patch.dict(sys.modules,serial=types.SimpleNamespace(Serial=Port),usb=types.SimpleNamespace(Device=Device,prevent_linux_hangup_reset=lambda s:None)), \
             patch.object(worker,'guard_port',lambda c:contextlib.nullcontext()),patch.object(sys,'__stdout__',self.log):worker.run(self.c)
    def test_success_one_arm_no_reset_or_control(self):
        self.invoke();self.assertEqual(len(self.calls),1);self.assertTrue(self.closed)
        self.assertFalse(self.s['io']['gpio_active']);self.assertIn('arm_saved_waiting_operator_en',self.log.getvalue())
    def test_lost_reply_never_replays(self):
        with self.assertRaises(TimeoutError):self.invoke(lost_reply=True)
        self.assertEqual(len(self.calls),1);self.assertTrue(self.closed)
    def test_wrong_identity_no_arm(self):
        self.c['expected_device_id']='0'*12
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.calls)
    def test_already_pending_no_arm(self):
        self.s['io']['armed_for_saved_layout']=True
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.calls)
    def test_clock_not_ready_no_arm(self):
        self.s['clock']['synchronized']=False
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.calls)
    def test_stale_revision_no_arm(self):
        self.c['expected_revision']='f'*64
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.calls)
    def test_nonoff_defaults_before_open(self):
        self.c['profile']['relays'][0]['defaultValue']=True
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_approval_required(self):
        self.c['operator_present']=False
        with self.assertRaises(ValueError):worker.validate(self.c)

if __name__=='__main__':unittest.main()
