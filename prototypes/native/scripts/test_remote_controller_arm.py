#!/usr/bin/env python3
"""Fake transport only. Never opens USB, arms a device or toggles GPIO."""
import copy
import io
import sys
import time
import unittest
from unittest.mock import patch
import remote_controller_arm as arm

class Tests(unittest.TestCase):
    def setUp(self):
        profile={'hostname':'barn','timezone':'America/Los_Angeles','clock_source':'network','sensors_enabled':False,'relays':[{'pin':n,'value':False,'auto':False,'defaultValue':False,'defaultAuto':False} for n in range(4,13)]}
        self.cfg=dict(apply_confirmed=True,maintenance_confirmed=True,equipment_main_power_off=True,gpio_enable_authorized=True,manual_profile=profile,port='fake',expected_device_id='123456abcdef',expected_elf_sha256='a'*64)
        outer=self
        class Device:
            arms=[];armed=False;closed=False;lost=False;reboot=False
            def __init__(self,port,controller=False):assert controller
            def close(self):self.closed=True
            def command(self,body):
                self.arms.append(body);self.armed=True
                if self.lost:raise TimeoutError('lost reply')
                return {'status':200,'data':{'success':True,'restart_required':True}}
            def request(self,method,path):
                assert method=='GET'
                return {'status':200,'data':copy.deepcopy({
                    '/api/ota/status':{'boot_id':'f'*16 if self.reboot and self.armed else 'b'*16,'elf_sha256':outer.cfg['expected_elf_sha256'],'healthy':True,'running_state':'valid','uploading':False,'running_slot':'ota_0','boot_slot':'ota_0'},
                    '/api/io/status':{'device_id':'123456abcdef','layout_hash':'c'*64,'gpio_compiled':True,'gpio_active':False,'armed_for_saved_layout':self.armed,'cleanup_failed':False},
                    '/api/config':{'device_role':'relay-controller','simulated':True,'restart_required':False,'active_hostname':'barn'},
                    '/api/profile/edit':{'profile':outer.cfg['manual_profile'],'boot_id':'b'*16,'revision':'d'*64},
                    '/api/profile':outer.cfg['manual_profile'],
                    '/api/watchdog/status':{'timeout_mask':0,'fault_injection':False},
                    '/api/time/status':{'timezone_confirmed':True,'synchronized':True,'schedule_clock_valid':True,'unix_seconds':int(time.time())},
                }[path])}
        self.Device=Device
    def run_arm(self):
        with patch.object(sys,'__stdout__',io.StringIO()) as out:arm.run(self.cfg,self.Device)
        return out.getvalue()
    def test_success_exactly_one_arm_no_reset(self):
        text=self.run_arm();self.assertEqual(len(self.Device.arms),1);body=self.Device.arms[0]
        self.assertEqual(body,{'op':'io_arm','device_id':'123456abcdef','layout_hash':'c'*64,'boot_id':'b'*16,'confirm':'enable relay outputs after reboot'})
        self.assertIn('arm_saved_reboot_required',text);self.assertIn('"reset_command_issued": false',text)
    def test_missing_permission_refused(self):
        self.cfg['equipment_main_power_off']=False
        with self.assertRaises(ValueError):self.run_arm()
        self.assertEqual(self.Device.arms,[])
    def test_auto_or_on_default_refused(self):
        for k in ('value','auto','defaultValue','defaultAuto'):
            self.cfg['manual_profile']['relays'][0][k]=True
            with self.assertRaises(ValueError):self.run_arm()
            self.cfg['manual_profile']['relays'][0][k]=False
        self.assertEqual(self.Device.arms,[])
    def test_wrong_identity_refused(self):
        self.cfg['expected_device_id']='0'*12
        with self.assertRaises(ValueError):self.run_arm()
        self.assertEqual(self.Device.arms,[])
    def test_lost_arm_reply_not_replayed(self):
        self.Device.lost=True
        with self.assertRaises(TimeoutError):self.run_arm()
        self.assertEqual(len(self.Device.arms),1)
    def test_reboot_after_ack_not_rearmed(self):
        self.Device.reboot=True
        with self.assertRaises(ValueError):self.run_arm()
        self.assertEqual(len(self.Device.arms),1)

if __name__=='__main__':unittest.main()
