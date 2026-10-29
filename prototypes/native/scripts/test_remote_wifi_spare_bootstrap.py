#!/usr/bin/env python3
import copy,hashlib,io,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import remote_wifi_spare_bootstrap as worker
class Port:
 def __init__(self):self.master,self.slave=os.openpty()
 def fileno(self):return self.slave
 def read(self,n):return b'BENCH_PASS all\nRUNTIME_READY test\n'
 def close(self):os.close(self.master);os.close(self.slave)
class Esp:
 CHIP_NAME='ESP32-S3'
 def __init__(self):self._port=Port();self.reset=False
 def read_mac(self):return bytes.fromhex('021122334455')
 def get_security_info(self):return {'parsed_flags':{'SECURE_BOOT_EN':False},'flash_crypt_cnt':0}
 def run_stub(self):return self
 def flash_md5sum(self,a,b):return 'a'*32
 def hard_reset(self):self.reset=True
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);d=Path(self.tmp.name);files=[]
  for off in ['0x0','0x8000','0xf000','0x20000']:
   p=d/(off+'.bin');p.write_bytes(off.encode());files.append(dict(offset=off,file=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  self.c=dict(purpose='isolated-wifi-spare',apply_confirmed=True,bare_usb_only_confirmed=True,backup_verified=True,excluded_chip_macs=['02:00:00:00:00:01','02:00:00:00:00:02'],port='/fake',artifact_directory=str(d),plan=dict(expected_chip_mac='02:11:22:33:44:55',original_device_md5='a'*32,image={'contract':'relay-profile1'},gpio_to_remain_disarmed=True,files=files));self.calls=[]
 def invoke(self,change=None):
  e=Esp()
  if change:change(e)
  fake=types.SimpleNamespace(detect_chip=lambda **kw:e,cmds=types.SimpleNamespace(detect_flash_size=lambda esp:'16MB'),main=lambda args,esp:self.calls.append(args))
  with patch.dict(sys.modules,esptool=fake),patch.object(sys,'__stdout__',io.StringIO()):worker.run(self.c)
  return e
 def test_success(self):
  e=self.invoke();self.assertTrue(e.reset);self.assertEqual(len(self.calls),3)
 def test_wrong_identity_no_erase(self):
  with self.assertRaises(ValueError):self.invoke(lambda e:setattr(e,'read_mac',lambda:bytes(6)))
  self.assertFalse(self.calls)
 def test_changed_backup_no_erase(self):
  with self.assertRaises(ValueError):self.invoke(lambda e:setattr(e,'flash_md5sum',lambda a,b:'b'*32))
  self.assertFalse(self.calls)
 def test_security_no_erase(self):
  with self.assertRaises(ValueError):self.invoke(lambda e:setattr(e,'get_security_info',lambda:{'parsed_flags':{'SECURE_BOOT_EN':True},'flash_crypt_cnt':0}))
  self.assertFalse(self.calls)
 def test_production_identity_excluded(self):
  self.c['excluded_chip_macs'].append(self.c['plan']['expected_chip_mac'])
  with self.assertRaises(ValueError):worker.run(self.c)
 def test_mutated_artifact_no_open(self):
  Path(self.c['plan']['files'][0]['file']).write_bytes(b'changed')
  with self.assertRaises(ValueError):worker.run(self.c)
if __name__=='__main__':unittest.main()
