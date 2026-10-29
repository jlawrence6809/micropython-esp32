#!/usr/bin/env python3
"""Offline real-image/fake-SDK/PTY app-repair safety regression tests."""
import contextlib
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import controller_release
import remote_relay_x8_app_repair as worker
from relay_x8_inert_nvs import inspect
from test_relay_x8_inert_nvs import fixture, entry
ROOT=Path(__file__).resolve().parents[1]

class Port:
    def __init__(self,**kw):self.m,self.s=os.openpty();self.closed=False
    def open(self):pass
    def fileno(self):return self.s
    def close(self):os.close(self.m);os.close(self.s);self.closed=True

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);d=Path(self.tmp.name)
        image=ROOT/'build-esp32-relay-x8-install/garden_native_probe.bin'
        old=ROOT/'build-esp32-controller/garden_native_probe.bin'
        if not image.exists() or not old.exists():self.skipTest('Build ESP32 controller images first')
        b=image.read_bytes();(d/image.name).write_bytes(b);self.md5=hashlib.md5(b).hexdigest()
        self.c=dict(purpose='relay-x8-failed-first-boot-app-repair',apply_confirmed=True,loads_disconnected=True,
                    backup_verified=True,remain_unarmed=True,expected_chip_mac='02:11:22:33:44:55',expected_chip_revision=301,
                    app_offset=0x20000,slot_bytes=0x180000,artifact_directory=str(d),port='/fake',
                    image=dict(file=image.name,audit=controller_release.image_info(b,'esp32')),
                    previous_image=controller_release.image_info(old.read_bytes(),'esp32'),
                    current_ranges=[dict(name='bootloader',offset=0x1000,bytes=20000,md5='a'*32),
                                    dict(name='partition_table',offset=0x8000,bytes=3072,md5='b'*32),
                                    dict(name='previous_app',offset=0x20000,bytes=old.stat().st_size,md5='c'*32)])
        self.calls=[];self.port=None;self.log=io.StringIO()
    def invoke(self,wrong_id=False,security=False,changed=False,nvs_changed=False,wrong_geo=False,fail_write=False,nvs_unsafe=False):
        outer=self;c=self.c
        class Esp:
            CHIP_NAME='ESP32';secure_download_mode=False
            def __init__(self,p,**kw):outer.port=p;self.written=False
            def connect(self,**kw):outer.assertEqual(kw,dict(mode='no_reset',attempts=1))
            def read_mac(self):return bytes.fromhex('021122334455') if not wrong_id else bytes(6)
            def get_chip_revision(self):return 301
            def get_secure_boot_enabled(self):return security
            def get_flash_encryption_enabled(self):return False
            def get_encrypted_download_disabled(self):return False
            def run_stub(self):return self
            def flash_md5sum(self,off,n):
                if off==0x20000 and self.written:return outer.md5
                for x in c['current_ranges']:
                    if off==x['offset'] and n==x['bytes']:return '0'*32 if changed else x['md5']
                if off==0x9000:
                    if nvs_changed:return '0'*32
                    if 'inert_nvs' in c:return hashlib.md5(fixture()).hexdigest()
                if off==0xf000:return 'd'*32
                return hashlib.md5(b'\xff'*n).hexdigest()
            def read_flash(self,off,n):
                outer.assertEqual((off,n),(0x9000,0x6000))
                if nvs_unsafe:return fixture([entry(0,1,b'bench',1),entry(1,4,b'arm_v1',1),entry(0,1,b'clock',2)])
                return fixture()
            def hard_reset(self):raise AssertionError('No reset allowed')
        def main(args,esp):
            self.assertEqual(esp.WRITE_FLASH_ATTEMPTS,1);self.assertEqual(fake.loader.WRITE_BLOCK_ATTEMPTS,1)
            self.assertFalse(any(x in args for x in ['erase_flash','--erase-all','hard_reset']))
            self.assertEqual(args[-2],'0x20000');self.calls.append(args)
            if 'write_flash' in args:
                if fail_write:raise SystemExit(2)
                esp.written=True
        fake=types.SimpleNamespace(ESP32ROM=Esp,loader=types.SimpleNamespace(WRITE_BLOCK_ATTEMPTS=3),
            cmds=types.SimpleNamespace(detect_flash_size=lambda e:'16MB' if wrong_geo else '4MB'),main=main)
        with patch.dict(sys.modules,esptool=fake,serial=types.SimpleNamespace(Serial=Port)), \
             patch.object(worker,'guard_port',lambda c:contextlib.nullcontext()),patch.object(sys,'__stdout__',self.log):
            worker.run(c)
    def test_success_app_only_no_reset_closed(self):
        self.invoke();self.assertEqual(len(self.calls),2);self.assertTrue(self.port.closed)
        self.assertIn('flash_verified_waiting_operator_en',self.log.getvalue())
    def test_wrong_chip_no_write(self):
        with self.assertRaises(ValueError):self.invoke(wrong_id=True)
        self.assertFalse(self.calls);self.assertTrue(self.port.closed)
    def test_security_no_write(self):
        with self.assertRaises(ValueError):self.invoke(security=True)
        self.assertFalse(self.calls)
    def test_changed_old_artifact_no_write(self):
        with self.assertRaises(ValueError):self.invoke(changed=True)
        self.assertFalse(self.calls)
    def test_nonblank_nvs_no_write(self):
        with self.assertRaises(ValueError):self.invoke(nvs_changed=True)
        self.assertFalse(self.calls)
    def test_wrong_geometry_no_write(self):
        with self.assertRaises(ValueError):self.invoke(wrong_geo=True)
        self.assertFalse(self.calls)
    def test_write_uncertainty_no_replay(self):
        with self.assertRaises(SystemExit):self.invoke(fail_write=True)
        self.assertEqual(len(self.calls),1);self.assertTrue(self.port.closed)
    def test_reviewed_schema_only_preserved(self):
        self.c['inert_nvs']=inspect(fixture());self.invoke();self.assertEqual(len(self.calls),2)
        self.assertIn('strict_schema_only_nvs_verified',self.log.getvalue())
    def test_reviewed_nvs_fence_changed_no_write(self):
        self.c['inert_nvs']=inspect(fixture());self.c['inert_nvs']['sha256']='0'*64
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.calls)
    def test_nvs_independently_parsed_not_just_flag(self):
        self.c['inert_nvs']=inspect(fixture())
        with self.assertRaises(ValueError):self.invoke(nvs_unsafe=True)
        self.assertFalse(self.calls)
    def test_wrong_offset_before_open(self):
        self.c['app_offset']=0x320000
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_mutated_new_image_before_open(self):
        (Path(self.c['artifact_directory'])/'garden_native_probe.bin').write_bytes(b'bad')
        with self.assertRaises(ValueError):worker.validate(self.c)
    def test_same_image_before_open(self):
        self.c['previous_image']=self.c['image']['audit']
        with self.assertRaises(ValueError):worker.validate(self.c)

if __name__=='__main__':unittest.main()
