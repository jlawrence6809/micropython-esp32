#!/usr/bin/env python3
"""Offline-only termios tests; never opens a serial adapter."""
import termios
import unittest
from unittest.mock import Mock, patch
from usb import prevent_linux_hangup_reset, Device
from serial import SerialTimeoutException

class HangupTests(unittest.TestCase):
    def test_clears_only_hupcl(self):
        port=Mock();port.fileno.return_value=71
        attrs=[1,2,termios.HUPCL|termios.CREAD|termios.CLOCAL,4,5,6,[]]
        with patch('usb.sys.platform','linux'), patch('termios.tcgetattr',return_value=attrs), patch('termios.tcsetattr') as put:
            prevent_linux_hangup_reset(port)
            put.assert_called_once_with(71,termios.TCSANOW,[1,2,termios.CREAD|termios.CLOCAL,4,5,6,[]])
    def test_already_clear_no_write(self):
        with patch('usb.sys.platform','linux'), patch('termios.tcgetattr',return_value=[0,0,termios.CREAD,0,0,0,[]]), patch('termios.tcsetattr') as put:
            prevent_linux_hangup_reset(Mock());put.assert_not_called()
    def test_other_platform_unchanged(self):
        with patch('usb.sys.platform','darwin'),patch('termios.tcgetattr') as get:
            prevent_linux_hangup_reset(Mock());get.assert_not_called()
    def test_stalled_write_bounded_and_never_replayed(self):
        dev=Device.__new__(Device);dev.serial=Mock();dev.sequence=0
        dev.serial.write.side_effect=SerialTimeoutException('blocked USB endpoint')
        with self.assertRaises(SerialTimeoutException):dev.command({'op':'request','method':'GET','path':'/api/config'})
        self.assertEqual(dev.serial.write_timeout,8)
        self.assertEqual(dev.serial.write.call_count,1);dev.serial.readline.assert_not_called()
    def test_error_not_silenced(self):
        with patch('usb.sys.platform','linux'),patch('termios.tcgetattr',side_effect=OSError('TTY error')):
            with self.assertRaises(OSError):prevent_linux_hangup_reset(Mock())

if __name__=='__main__':unittest.main()
