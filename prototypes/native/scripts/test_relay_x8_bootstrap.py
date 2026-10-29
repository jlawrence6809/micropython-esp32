#!/usr/bin/env python3
"""Offline real-artifact + fake-SDK/PTY bootstrap tests; no hardware operations."""
import contextlib
import copy
import hashlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import controller_release
import remote_relay_x8_bootstrap as worker

BUILD = Path(__file__).resolve().parents[1] / 'build-esp32-controller'

class Port:
    def __init__(self, **kw):
        self.master, self.slave = os.openpty(); self.closed = False; self.opened = False
    def fileno(self): return self.slave
    def open(self): self.opened = True
    def close(self):
        os.close(self.master); os.close(self.slave); self.closed = True

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (BUILD/'garden_native_probe.bin').exists():
            raise unittest.SkipTest('Build the original ESP32 controller first')
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name); files = []
        for off, source in [('0x1000','bootloader/bootloader.bin'), ('0x8000','partition_table/partition-table.bin'),
                            ('0xf000','ota_data_initial.bin'), ('0x20000','garden_native_probe.bin')]:
            p = d/Path(source).name; shutil.copyfile(BUILD/source,p)
            files.append(dict(offset=off,file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        self.c = dict(purpose='relay-x8-original-esp32', apply_confirmed=True, loads_disconnected=True,
                      external_12v_confirmed=True, adapter_power_pins_disconnected=True, backup_verified=True,
                      remain_unarmed=True, expected_chip_mac='02:11:22:33:44:55', expected_chip_revision=301,
                      original_device_md5='a'*32, artifact_directory=str(d), port='/fake', files=files,
                      image=controller_release.image_info((d/'garden_native_probe.bin').read_bytes(),'esp32'))
        self.calls = []; self.port = None; self.logs = io.StringIO()
    def invoke(self, alter=None, fail_write=False):
        c=self.c; outer=self
        class Esp:
            CHIP_NAME='ESP32'; secure_download_mode=False
            def __init__(self, port, **kw): outer.port=port; self._port=port
            def connect(self, **kw): outer.assertEqual(kw,dict(mode='no_reset',attempts=1))
            def read_mac(self): return bytes.fromhex('021122334455')
            def get_chip_revision(self): return 301
            def get_secure_boot_enabled(self): return False
            def get_flash_encryption_enabled(self): return False
            def get_encrypted_download_disabled(self): return False
            def run_stub(self): return self
            def flash_md5sum(self, addr, n):
                if addr==0 and n==4194304:return 'a'*32
                if addr==0x9000:return hashlib.md5(b'\xff'*0x6000).hexdigest()
                f=next(f for f in c['files'] if int(f['offset'],16)==addr)
                return hashlib.md5((Path(c['artifact_directory'])/f['file']).read_bytes()).hexdigest()
            def hard_reset(self): raise AssertionError('Never reset this adapter')
        if alter:alter(Esp)
        def main(args,esp):
            self.assertEqual(esp.WRITE_FLASH_ATTEMPTS,1);self.assertEqual(fake.loader.WRITE_BLOCK_ATTEMPTS,1)
            self.calls.append(args)
            if fail_write and 'write_flash' in args:raise SystemExit(2)
        fake=types.SimpleNamespace(ESP32ROM=Esp, loader=types.SimpleNamespace(WRITE_BLOCK_ATTEMPTS=3),
                                   cmds=types.SimpleNamespace(detect_flash_size=lambda esp:'4MB'),main=main)
        with patch.dict(sys.modules,esptool=fake,serial=types.SimpleNamespace(Serial=Port)), \
             patch.object(worker,'guard_port',lambda c:contextlib.nullcontext()), \
             patch.object(sys,'__stdout__',self.logs):
            worker.run(self.c)
    def test_success_once_no_reset_closed(self):
        self.invoke();self.assertEqual(len(self.calls),3);self.assertTrue(self.port.closed)
        self.assertIn('flash_verified_waiting_operator_en',self.logs.getvalue())
        self.assertTrue(all('--after' in args and 'no_reset_stub' in args for args in self.calls))
    def test_wrong_identity_no_erase(self):
        with self.assertRaises(ValueError):self.invoke(lambda e:setattr(e,'read_mac',lambda s:bytes(6)))
        self.assertFalse(self.calls);self.assertTrue(self.port.closed)
    def test_wrong_revision_no_erase(self):
        with self.assertRaises(ValueError):self.invoke(lambda e:setattr(e,'get_chip_revision',lambda s:300))
        self.assertFalse(self.calls)
    def test_security_no_erase(self):
        for name in ['get_secure_boot_enabled','get_flash_encryption_enabled','get_encrypted_download_disabled']:
            with self.subTest(name=name),self.assertRaises(ValueError):
                self.invoke(lambda e:setattr(e,name,lambda s:True))
        self.assertFalse(self.calls)
    def test_changed_flash_no_erase(self):
        with self.assertRaises(ValueError):self.invoke(lambda e:setattr(e,'flash_md5sum',lambda *a:'b'*32))
        self.assertFalse(self.calls)
    def test_write_failure_no_replay_or_verify(self):
        with self.assertRaises(SystemExit):self.invoke(fail_write=True)
        self.assertEqual(len(self.calls),2);self.assertTrue(self.port.closed)
        self.assertIn('stopped_inspect_no_replay',self.logs.getvalue())
    def test_mutated_artifact_no_open(self):
        (Path(self.c['artifact_directory'])/'bootloader.bin').write_bytes(b'bad')
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_s3_offsets_rejected(self):
        self.c['files'][0]['offset']='0x0'
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_bench_contract_rejected(self):
        self.c['image']['contract']='native-profile1'
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_unloaded_gate_required(self):
        self.c['loads_disconnected']=False
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_path_escape_rejected(self):
        self.c['files'][0]['file']='../bootloader.bin'
        with self.assertRaises(ValueError):worker.validate(self.c)

if __name__=='__main__':unittest.main()
