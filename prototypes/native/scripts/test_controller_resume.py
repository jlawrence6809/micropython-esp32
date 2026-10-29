#!/usr/bin/env python3
"""Offline-only resume gating and no-replay tests, fake API/esptool."""
import copy
import hashlib
import io
import json
import sys
import types
import unittest
from unittest.mock import Mock,patch
import remote_controller_resume as resume

MAC='11:22:33:44:55:66'

class Device:
    def __init__(self):
        self.profile=resume.factory_profile();self.provisioned=False;self.posts=[];self.loss=None
    def close(self):pass
    def wait_healthy(self):pass
    def request(self,method,path,body=''):
        if method=='POST':
            self.posts.append(path)
            if path=='/api/profile/import':
                self.profile=json.loads(body)
                if self.loss=='import':raise TimeoutError()
            return {'status':200,'data':{'success':True,'outputs_applied':True,'layout_hash':'b'*64}}
        data={
            '/api/config':{'device_role':'relay-controller','simulated':True,'restart_required':True},
            '/api/io/status':{'device_id':MAC.replace(':',''),'gpio_compiled':True,'gpio_active':False,'armed_for_saved_layout':False,'cleanup_failed':False,'layout_hash':'b'*64},
            '/api/ota/status':{'elf_sha256':'a'*64,'healthy':True,'running_state':'valid','uploading':False,'boot_id':'c'*16,'running_slot':'ota_0','boot_slot':'ota_0'},
            '/api/watchdog/status':{'fault_injection':False,'timeout_mask':0},
            '/api/profile':self.profile,
            '/api/wifi/status':{'provisioned':self.provisioned,'sta_connected':self.provisioned,'sta_ssid':'unit'},
        }[path]
        return {'status':200,'data':copy.deepcopy(data)}
    def command(self,obj):
        assert obj['op']=='provision';self.posts.append('provision');self.provisioned=True
        if self.loss=='credentials':raise TimeoutError()
        return {'status':200,'data':{'success':True}}

class Tests(unittest.TestCase):
    def setUp(self):
        wanted=resume.factory_profile();wanted['hostname']='barn';wanted['relays']=[dict(wanted['relays'][0],pin=p) for p in range(4,13)]
        self.cfg={'plan':{'expected_chip_mac':MAC,'image':{'elf_sha256':'a'*64}},'profile':wanted,'wifi':{'ssid':'unit','password':'unit'}};self.dev=Device();self.events=[]
    def emit(self,stage,**extra):self.events.append(stage)
    def test_factory_restore_once(self):
        resume.restore(self.dev,self.cfg,self.emit);self.assertEqual(self.events[-1],'confirmed');self.assertEqual(self.dev.posts.count('/api/profile/import'),1);self.assertEqual(self.dev.posts.count('provision'),1)
    def test_already_restored_no_mutations(self):
        self.dev.profile=copy.deepcopy(self.cfg['profile']);self.dev.provisioned=True
        resume.restore(self.dev,self.cfg,self.emit);self.assertEqual(self.dev.posts,[]);self.assertEqual(self.events[-1],'confirmed')
    def test_unknown_profile_not_overwritten(self):
        self.dev.profile['hostname']='other'
        with self.assertRaises(ValueError):resume.restore(self.dev,self.cfg,self.emit)
        self.assertEqual(self.dev.posts,[])
    def test_existing_credentials_factory_refused(self):
        self.dev.provisioned=True
        with self.assertRaises(ValueError):resume.restore(self.dev,self.cfg,self.emit)
        self.assertEqual(self.dev.posts,[])
    def test_lost_import_not_replayed(self):
        self.dev.loss='import'
        with self.assertRaises(TimeoutError):resume.restore(self.dev,self.cfg,self.emit)
        self.assertEqual(self.dev.posts.count('/api/profile/import'),1);self.assertNotIn('provision',self.dev.posts)
    def test_lost_credentials_not_replayed(self):
        self.dev.loss='credentials'
        with self.assertRaises(TimeoutError):resume.restore(self.dev,self.cfg,self.emit)
        self.assertEqual(self.dev.posts.count('provision'),1)
    def test_wrong_identity_before_mutation(self):
        self.cfg['plan']['expected_chip_mac']='00:00:00:00:00:00'
        with self.assertRaises(ValueError):resume.restore(self.dev,self.cfg,self.emit)
        self.assertEqual(self.dev.posts,[])
    def test_values_not_replayed(self):
        self.dev.profile=copy.deepcopy(self.cfg['profile']);self.dev.profile['relays'][0]['value']=True;self.dev.provisioned=True
        resume.restore(self.dev,self.cfg,self.emit);self.assertTrue(self.dev.profile['relays'][0]['value']);self.assertEqual(self.dev.posts,[])
    def test_supported_reset_only_after_digest_check(self):
        cfg=copy.deepcopy(self.cfg);cfg.update(maintenance_confirmed=True,main_power_isolated=True,backup_verified=True,apply_confirmed=True,port='fake',artifact_hex={'0x0':b'unit'.hex()});cfg['plan']['files']=[{'offset':'0x0','bytes':4}]
        esp=Mock();esp.CHIP_NAME='ESP32-S3';esp.read_mac.return_value=bytes.fromhex(MAC.replace(':',''));esp.get_security_info.return_value={'parsed_flags':{'SECURE_BOOT_EN':False},'flash_crypt_cnt':0};esp.run_stub.return_value=esp;esp.flash_md5sum.return_value=hashlib.md5(b'unit').hexdigest();esp._port.read.return_value=b'BENCH_PASS ok\nRUNTIME_READY ok\n'
        tool=types.SimpleNamespace(detect_chip=Mock(return_value=esp),cmds=types.SimpleNamespace(detect_flash_size=Mock(return_value='16MB')))
        sink=io.StringIO()
        with patch.dict(sys.modules,{'esptool':tool}),patch.object(sys,'__stdout__',sink),patch.object(sys,'stderr',io.StringIO()),patch.object(resume,'restore') as restore:
            resume.run(cfg,Device,lambda _:None);esp.watchdog_reset.assert_called_once();esp.hard_reset.assert_not_called();restore.assert_called_once()
        # OTA-selection data changes on boot; it is not an immutable artifact.
        cfg['plan']['files'].append({'offset':'0xf000','bytes':4})
        cfg['artifact_hex']['0xf000']=b'unit'.hex()
        esp.reset_mock();esp.flash_md5sum.side_effect=lambda offset,size:hashlib.md5(b'unit').hexdigest() if offset==0 else '0'*32
        with patch.dict(sys.modules,{'esptool':tool}),patch.object(sys,'__stdout__',sink),patch.object(sys,'stderr',io.StringIO()),patch.object(resume,'restore'):
            resume.run(cfg,Device,lambda _:None)
            esp.watchdog_reset.assert_called_once()
        esp.reset_mock();esp.flash_md5sum.side_effect=None;esp.flash_md5sum.return_value='0'*32
        with patch.dict(sys.modules,{'esptool':tool}),patch.object(sys,'__stdout__',sink),patch.object(sys,'stderr',io.StringIO()):
            with self.assertRaises(ValueError):resume.run(cfg,Device,lambda _:None)
            esp.watchdog_reset.assert_not_called()

if __name__=='__main__':unittest.main()
