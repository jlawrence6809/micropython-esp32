#!/usr/bin/env python3
"""Offline port-selection/privacy regression; no serial adapter is opened."""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

class Tests(unittest.TestCase):
    def load(self,env):
        serial=types.SimpleNamespace(Serial=Mock())
        spec=importlib.util.spec_from_file_location('usb_port_test',Path(__file__).with_name('usb.py'))
        module=importlib.util.module_from_spec(spec)
        with patch.dict(os.environ,env,clear=True),patch.dict(sys.modules,serial=serial):spec.loader.exec_module(module)
        return module,serial
    def test_no_implicit_device_selection(self):
        module,serial=self.load({});self.assertIsNone(module.DEFAULT_PORT)
        for value in (None,''):
            with self.assertRaisesRegex(ValueError,'Explicit'):module.Device(value)
        serial.Serial.assert_not_called()
    def test_explicit_environment_port(self):
        module,serial=self.load({'GARDEN_BENCH_PORT':'/test/approved-port'})
        self.assertEqual(module.DEFAULT_PORT,'/test/approved-port');serial.Serial.assert_not_called()

if __name__=='__main__':unittest.main()
