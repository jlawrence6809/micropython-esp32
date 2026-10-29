#!/usr/bin/env python3
"""Offline inert profile gates, including second board's distinct hostname."""
import json
from pathlib import Path
import unittest
from remote_relay_x8_memory_test import validate

class Tests(unittest.TestCase):
    def setUp(self):
        self.c=dict(purpose='relay-x8-unarmed-memory-test',loads_disconnected=True,apply_confirmed=True,
                    profile=json.loads((Path(__file__).resolve().parents[1]/'profiles/relay_x8_unarmed.json').read_text()))
    def test_first_board_default_retained(self):validate(self.c)
    def test_second_unique_name_explicit(self):
        self.c['reviewed_hostname']='relay-x8-spare';self.c['profile']['hostname']='relay-x8-spare';validate(self.c)
    def test_name_mismatch_rejected(self):
        self.c['reviewed_hostname']='relay-x8-spare'
        with self.assertRaises(ValueError):validate(self.c)
    def test_production_name_rejected(self):
        self.c['reviewed_hostname']='barn';self.c['profile']['hostname']='barn'
        with self.assertRaises(ValueError):validate(self.c)
    def test_noninert_default_rejected(self):
        self.c['profile']['relays'][0]['defaultAuto']=True
        with self.assertRaises(ValueError):validate(self.c)
    def test_other_map_rejected(self):
        self.c['profile']['relays'][0]['pin']=1
        with self.assertRaises(ValueError):validate(self.c)
    def test_approval_required(self):
        self.c['loads_disconnected']=False
        with self.assertRaises(ValueError):validate(self.c)

if __name__=='__main__':unittest.main()
