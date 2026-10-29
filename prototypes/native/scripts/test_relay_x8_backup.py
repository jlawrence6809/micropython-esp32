#!/usr/bin/env python3
"""Fake SDK/serial read-only backup tests, no devices or raw private fixtures."""
import contextlib
import hashlib
import io
import json
import sys
import types
import unittest
from unittest.mock import patch
import remote_relay_x8_backup as w

class Tests(unittest.TestCase):
    def setUp(self):
        self.c=dict(purpose='relay-x8-readonly-backup',maintenance_confirmed=True,loads_disconnected=True,
                    external_12v_confirmed=True,adapter_power_pins_disconnected=True,mode='backup',port='/fake',
                    excluded_chip_macs=['00:00:00:00:00:00'],expected_chip_mac='11:22:33:44:55:66')
        self.data=b'\xff'*4194304;self.baud=[];self.closed=False;self.stub=False;self.bad_md5=False;self.size='4MB';self.attached=False;self.pads=(0,0,0,0,0)
    def invoke(self):
        outer=self
        class Serial:
            def __init__(self,**kw):pass
            def open(self):pass
            def close(self):outer.closed=True
            def fileno(self):return 42
        class ESP:
            CHIP_NAME='ESP32';secure_download_mode=False
            def __init__(self,s,baud):outer.assertEqual(baud,115200)
            def connect(self,mode,attempts):outer.assertEqual((mode,attempts),('no_reset',1))
            def read_mac(self):return bytes.fromhex('112233445566')
            def get_chip_revision(self):return 301
            def get_crystal_freq(self):return 40
            def get_secure_boot_enabled(self):return False
            def get_flash_encryption_enabled(self):return False
            def get_encrypted_download_disabled(self):return False
            def get_chip_spi_pads(self):return outer.pads
            def flash_spi_attach(self,n):outer.assertEqual(n,0);outer.attached=True
            def run_stub(self):outer.stub=True;return self
            def change_baud(self,n):outer.baud.append(n)
            def read_flash(self,start,size):outer.assertEqual((start,size),(0,4194304));return outer.data
            def flash_md5sum(self,start,size):return '0'*32 if outer.bad_md5 else hashlib.md5(outer.data).hexdigest()
        out=io.BytesIO();sink=io.TextIOWrapper(out,write_through=True);self.out=out
        with patch.dict(sys.modules,serial=types.SimpleNamespace(Serial=Serial),esptool=types.SimpleNamespace(ESP32ROM=ESP,__version__='fake',cmds=types.SimpleNamespace(detect_flash_size=lambda e:self.size if self.attached else None))), \
             patch.object(w,'guard_port',lambda c:contextlib.nullcontext()),patch('termios.tcgetattr',return_value=[0,0,128]),patch('termios.tcsetattr'), \
             patch.object(sys,'__stdout__',sink),contextlib.redirect_stderr(io.StringIO()):
            try:w.run(self.c)
            finally:self.output=out.getvalue();sink.detach()
    def test_backup_full_digest_baud_restore(self):
        self.invoke();self.assertEqual(self.output,self.data);self.assertEqual(self.baud,[460800,115200]);self.assertTrue(self.closed)
    def test_identify_no_stub_no_baud_change(self):
        self.c['mode']='identify';self.invoke();self.assertFalse(self.stub);self.assertFalse(self.baud);self.assertEqual(json.loads(self.output)['flash_bytes'],4194304)
    def test_reused_device_rejected(self):
        self.c['excluded_chip_macs'].append(self.c['expected_chip_mac'])
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.stub);self.assertEqual(self.output,b'')
    def test_wrong_expected_identity_rejected(self):
        self.c['expected_chip_mac']='aa:bb:cc:dd:ee:ff'
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.stub)
    def test_nondefault_spi_pads_rejected(self):
        self.pads=(1,2,3,4,5)
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.attached);self.assertFalse(self.stub)
    def test_geometry_rejected(self):
        self.size='8MB'
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.stub)
    def test_bad_md5_never_streams(self):
        self.bad_md5=True
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.output,b'')
    def test_short_read_never_streams(self):
        self.data=b'x'
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.output,b'')
    def test_approval_required(self):
        self.c['loads_disconnected']=False
        with self.assertRaises(ValueError):w.run(self.c)

if __name__=='__main__':unittest.main()
