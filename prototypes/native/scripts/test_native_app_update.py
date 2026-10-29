#!/usr/bin/env python3
"""Offline fake-loader one-shot native USB app-update boundary tests."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock,patch
import remote_native_app_update as update

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);app=Path(self.tmp.name)/'app.bin';app.write_bytes(b'unit')
        self.cfg=dict(apply_confirmed=True,maintenance_confirmed=True,main_power_isolated=True,factory_unarmed_boot_observed=True,full_backup_verified=True,app_path=str(app),port='fake',expected_chip_mac='11:22:33:44:55:66',new_image={'bytes':4,'contract':'relay-profile1','image_sha256':hashlib.sha256(b'unit').hexdigest()},old_immutable=[{'offset':'0x20000','bytes':4,'md5':hashlib.md5(b'unit').hexdigest()}])
        self.esp=Mock();self.esp.CHIP_NAME='ESP32-S3';self.esp.read_mac.return_value=bytes.fromhex('112233445566');self.esp.get_security_info.return_value={'parsed_flags':{'SECURE_BOOT_EN':False},'flash_crypt_cnt':0};self.esp.run_stub.return_value=self.esp;self.esp.flash_md5sum.return_value=hashlib.md5(b'unit').hexdigest()
        self.tool=types.SimpleNamespace(detect_chip=Mock(return_value=self.esp),cmds=types.SimpleNamespace(detect_flash_size=Mock(return_value='16MB')),main=Mock())
        self.addCleanup(patch.stopall);patch.dict(sys.modules,{'esptool':self.tool}).start();patch.object(sys,'__stdout__',io.StringIO()).start();patch.object(sys,'stderr',io.StringIO()).start()
    def test_one_app_write_verify_reset_no_full_erase(self):
        update.run(self.cfg,lambda _:None);calls=[x.args[0] for x in self.tool.main.call_args_list]
        self.assertEqual([x[7] for x in calls],['write_flash','verify_flash']);self.assertEqual(sum('write_flash' in x for x in calls),1);self.assertTrue(all('0x20000' in x for x in calls));self.assertFalse(any('erase_flash' in x for x in calls));self.esp.hard_reset.assert_called_once()
    def test_unapproved_or_corrupt_never_opens(self):
        self.cfg['main_power_isolated']=False
        with self.assertRaises(ValueError):update.run(self.cfg,lambda _:None)
        self.cfg['main_power_isolated']=True;Path(self.cfg['app_path']).write_bytes(b'bad')
        with self.assertRaises(ValueError):update.run(self.cfg,lambda _:None)
        self.tool.detect_chip.assert_not_called()
    def test_wrong_chip_no_write(self):
        self.esp.read_mac.return_value=b'\0'*6
        with self.assertRaises(ValueError):update.run(self.cfg,lambda _:None)
        self.tool.main.assert_not_called()
    def test_changed_installed_image_no_write(self):
        self.esp.flash_md5sum.return_value='0'*32
        with self.assertRaises(ValueError):update.run(self.cfg,lambda _:None)
        self.tool.main.assert_not_called();self.esp.hard_reset.assert_not_called()
    def test_write_failure_never_replayed_or_reset(self):
        self.tool.main.side_effect=RuntimeError('uncertain')
        with self.assertRaises(RuntimeError):update.run(self.cfg,lambda _:None)
        self.assertEqual(self.tool.main.call_count,1);self.esp.hard_reset.assert_not_called()

if __name__=='__main__':unittest.main()
