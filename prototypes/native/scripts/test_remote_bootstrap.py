#!/usr/bin/env python3
"""Offline fake esptool/TTY/API tests. Never touches serial or network."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import remote_flash_backup as backup
import remote_controller_bootstrap as bootstrap

MAC='11:22:33:44:55:66'

class Sink:
    def __init__(self):self.text=io.StringIO();self.buffer=io.BytesIO()
    def write(self,s):return self.text.write(s)
    def flush(self):pass

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);p=Path(self.tmp.name)
        self.esp=Mock();self.esp.CHIP_NAME='ESP32-S3';self.esp.read_mac.return_value=bytes.fromhex(MAC.replace(':',''));self.esp.get_security_info.return_value={'parsed_flags':{'SECURE_BOOT_EN':False},'flash_crypt_cnt':0};self.esp.run_stub.return_value=self.esp;self.esp._port.read.return_value=b'BENCH_PASS ok\nRUNTIME_READY ok\n'
        self.tool=types.SimpleNamespace(detect_chip=Mock(return_value=self.esp),cmds=types.SimpleNamespace(detect_flash_size=Mock(return_value='16MB')),main=Mock(),__version__='4.12.0')
        self.term=types.SimpleNamespace(HUPCL=16,TCSANOW=0,tcgetattr=Mock(return_value=[0,0,16,0,0,0,[]]),tcsetattr=Mock())
        self.sink=Sink();self.addCleanup(patch.stopall);patch.dict(sys.modules,{'esptool':self.tool,'termios':self.term}).start();patch.object(sys,'__stdout__',self.sink).start();patch.object(sys,'stderr',io.StringIO()).start()
        files=[]
        for i,offset in enumerate(['0x0','0x8000','0xf000','0x20000']):
            f=p/f'{i}.bin';f.write_bytes(b'fixture');files.append({'offset':offset,'file':str(f),'bytes':7,'sha256':hashlib.sha256(b'fixture').hexdigest()})
        self.profile={'hostname':'barn','relays':[{'pin':i,'rule':'return nil','value':False,'auto':False} for i in range(9)],'timezone':None,'clock_source':'manual','sensors_enabled':False}
        self.config={'apply_confirmed':True,'maintenance_confirmed':True,'main_power_isolated':True,'backup_verified':True,'port':'fake','artifact_directory':str(p),'plan':{'expected_chip_mac':MAC,'image':{'contract':'relay-profile1','elf_sha256':'a'*64},'gpio_to_remain_disarmed':True,'files':files},'profile':self.profile,'wifi':{'ssid':'unit','password':'unit'}}
        outer=self
        class Device:
            saved=False;provisioned=False;mutations=[];loss=False
            def wait_healthy(self):pass
            def close(self):pass
            def command(self,obj):
                self.mutations.append(obj['op']);self.provisioned=True
                return {'status':200,'data':{'success':True}}
            def request(self,method,path,body=''):
                if method=='POST':
                    self.mutations.append(path)
                    data={'success':True,'layout_hash':'b'*64,'outputs_applied':True}
                    if path=='/api/profile/import':
                        self.saved=True
                        if self.loss:raise TimeoutError('lost import ack')
                    return {'status':200,'data':data}
                data={
                  '/api/config':{'device_role':'relay-controller','simulated':True,'restart_required':self.saved},
                  '/api/io/status':{'device_id':MAC.replace(':',''),'gpio_compiled':True,'gpio_active':False,'armed_for_saved_layout':False,'cleanup_failed':False,'layout_hash':'b'*64},
                  '/api/ota/status':{'elf_sha256':'a'*64,'healthy':True,'running_state':'valid','uploading':False,'boot_id':'c'*16},
                  '/api/watchdog/status':{'fault_injection':False,'timeout_mask':0},
                  '/api/profile':outer.profile if self.saved else {},
                  '/api/wifi/status':{'provisioned':self.provisioned,'sta_connected':self.provisioned},
                }[path]
                return {'status':200,'data':copy.deepcopy(data)}
        self.Device=Device
    def test_success_single_order_no_reopen_or_arm(self):
        bootstrap.run(self.config,self.Device)
        calls=[x.args[0] for x in self.tool.main.call_args_list]
        self.assertEqual([x[7] for x in calls],['erase_flash','write_flash','verify_flash'])
        self.assertEqual(self.tool.detect_chip.call_count,1);self.assertEqual(self.esp.hard_reset.call_count,1)
        rows=[json.loads(x) for x in self.sink.text.getvalue().splitlines()];self.assertEqual(rows[-1]['stage'],'confirmed');self.assertFalse(rows[-1]['arming_issued']);self.assertEqual(rows[-1]['serial_reopens'],0)
        self.assertEqual(self.Device.mutations.count('/api/profile/import'),1);self.assertEqual(self.Device.mutations.count('provision'),1)
    def test_boot_read_explicitly_bounded(self):
        def read(_):
            self.assertEqual(self.esp._port.timeout,.25)
            return b'BENCH_PASS ok\nRUNTIME_READY ok\n'
        self.esp._port.read.side_effect=read
        bootstrap.run(self.config,self.Device)
        self.assertIn('confirmed',self.sink.text.getvalue())
    def test_missing_approval_no_open(self):
        for key in ['apply_confirmed','main_power_isolated','backup_verified','maintenance_confirmed']:
            cfg=copy.deepcopy(self.config);cfg[key]=False
            with self.assertRaises(ValueError):bootstrap.run(cfg,self.Device)
        self.tool.detect_chip.assert_not_called()
    def test_corrupt_artifact_no_open(self):
        Path(self.config['plan']['files'][0]['file']).write_bytes(b'bad')
        with self.assertRaises(ValueError):bootstrap.run(self.config,self.Device)
        self.tool.detect_chip.assert_not_called()
    def test_wrong_chip_or_security_no_erase(self):
        self.esp.read_mac.return_value=b'\0'*6
        with self.assertRaises(ValueError):bootstrap.run(self.config,self.Device)
        self.tool.main.assert_not_called()
        self.esp.read_mac.return_value=bytes.fromhex(MAC.replace(':',''));self.esp.get_security_info.return_value['flash_crypt_cnt']=1
        with self.assertRaises(ValueError):bootstrap.run(self.config,self.Device)
        self.tool.main.assert_not_called()
    def test_flash_failure_no_replay(self):
        self.tool.main.side_effect=RuntimeError('uncertain write')
        with self.assertRaises(RuntimeError):bootstrap.run(self.config,self.Device)
        self.assertEqual(self.tool.main.call_count,1);self.esp.hard_reset.assert_not_called();self.assertEqual(self.Device.mutations,[])
    def test_lost_import_ack_no_replay_or_credentials(self):
        self.Device.loss=True
        with self.assertRaises(TimeoutError):bootstrap.run(self.config,self.Device)
        self.assertEqual(self.Device.mutations.count('/api/profile/import'),1);self.assertNotIn('provision',self.Device.mutations)
    def test_backup_identity_only(self):
        backup.run({'mode':'identify','maintenance_confirmed':True,'port':'fake'})
        self.assertEqual(json.loads(self.sink.text.getvalue())['expected_chip_mac'],MAC);self.esp.read_flash.assert_not_called();self.esp.hard_reset.assert_not_called()
    def test_backup_independent_digest_stream(self):
        data=b'Z'*(16*1024*1024);self.esp.read_flash.return_value=data;self.esp.flash_md5sum.return_value=hashlib.md5(data).hexdigest()
        backup.run({'mode':'backup','maintenance_confirmed':True,'port':'fake','expected_chip_mac':MAC})
        self.assertEqual(self.sink.buffer.getvalue(),data);self.esp.flash_md5sum.assert_called_once_with(0,len(data));self.tool.main.assert_not_called();self.esp.hard_reset.assert_not_called()
    def test_bad_digest_streams_nothing(self):
        self.esp.read_flash.return_value=b'Z'*(16*1024*1024);self.esp.flash_md5sum.return_value='0'*32
        with self.assertRaises(ValueError):backup.run({'mode':'backup','maintenance_confirmed':True,'port':'fake','expected_chip_mac':MAC})
        self.assertEqual(self.sink.buffer.getvalue(),b'')
    def test_backup_wrong_identity_no_read(self):
        with self.assertRaises(ValueError):backup.run({'mode':'backup','maintenance_confirmed':True,'port':'fake','expected_chip_mac':'00:00:00:00:00:00'})
        self.esp.read_flash.assert_not_called()

if __name__=='__main__':unittest.main()
