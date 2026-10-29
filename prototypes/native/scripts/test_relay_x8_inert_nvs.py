#!/usr/bin/env python3
import struct
import unittest
import zlib
from relay_x8_inert_nvs import inspect


def entry(ns,typ,key,value):
    b=bytearray(b'\xff'*32);b[:4]=bytes([ns,typ,1,255]);b[8:24]=key.ljust(16,b'\0')
    struct.pack_into('<I' if typ==4 else '<B',b,24,value)
    struct.pack_into('<I',b,4,zlib.crc32(b[:4]+b[8:],0xffffffff));return b


def fixture(entries=None):
    if entries is None:entries=[entry(0,1,b'bench',1),entry(1,4,b'schema',1),entry(0,1,b'clock',2)]
    b=bytearray(b'\xff'*0x6000);struct.pack_into('<II',b,0,0xfffffffe,0);b[8]=0xfe
    struct.pack_into('<I',b,28,zlib.crc32(b[4:28],0xffffffff))
    for i,e in enumerate(entries):b[32+i//4]&=~(1<<(2*(i%4)));b[64+i*32:96+i*32]=e
    return b

class Tests(unittest.TestCase):
    def test_blank(self):self.assertEqual(inspect(b'\xff'*0x6000)['kind'],'blank')
    def test_schema_only(self):self.assertEqual(inspect(fixture())['kind'],'schema_only')
    def test_activation_key_rejected(self):
        with self.assertRaises(ValueError):inspect(fixture([entry(0,1,b'bench',1),entry(1,4,b'arm_v1',1),entry(0,1,b'clock',2)]))
    def test_profile_key_rejected(self):
        with self.assertRaises(ValueError):inspect(fixture([entry(0,1,b'bench',1),entry(1,4,b'profile_v1',1),entry(0,1,b'clock',2)]))
    def test_credentials_namespace_rejected(self):
        with self.assertRaises(ValueError):inspect(fixture([entry(0,1,b'net80211',1),entry(1,4,b'schema',1),entry(0,1,b'clock',2)]))
    def test_page_crc(self):
        b=fixture();b[4]^=1
        with self.assertRaises(ValueError):inspect(b)
    def test_entry_crc(self):
        b=fixture();b[88]^=1
        with self.assertRaises(ValueError):inspect(b)
    def test_erased_history(self):
        b=fixture();b[32]&=~2
        with self.assertRaises(ValueError):inspect(b)
    def test_other_schema(self):
        with self.assertRaises(ValueError):inspect(fixture([entry(0,1,b'bench',1),entry(1,4,b'schema',2),entry(0,1,b'clock',2)]))
    def test_wrong_namespace(self):
        with self.assertRaises(ValueError):inspect(fixture([entry(0,1,b'bench',1),entry(2,4,b'schema',1),entry(0,1,b'clock',2)]))
    def test_extra_record(self):
        with self.assertRaises(ValueError):inspect(fixture()+b'\xff'*4096)
    def test_hidden_empty_data(self):
        b=fixture();b[200]=0
        with self.assertRaises(ValueError):inspect(b)

if __name__=='__main__':unittest.main()
