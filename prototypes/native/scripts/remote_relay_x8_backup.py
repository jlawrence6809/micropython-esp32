#!/usr/bin/env python3
"""Read-only original-ESP32 ROM identity/full backup directly to caller's vault.
No flash/eFuse writes, GPIO arm, provisioning or reset. After backup, restore RAM
UART baud115200 and verify full device MD5 again, before streaming any raw bytes.
Caller supplies config via stdin, owns maintenance lock and exclusive vault journal.
"""
import contextlib
import hashlib
import json
import sys
from remote_relay_x8_bootstrap import guard_port, require


def run(c):
    require(c.get('purpose')=='relay-x8-readonly-backup' and c.get('maintenance_confirmed') is True and
            c.get('loads_disconnected') is True and c.get('external_12v_confirmed') is True and
            c.get('adapter_power_pins_disconnected') is True,'Approved isolated maintenance required')
    require(c.get('mode') in ['identify','backup'],'Read-only mode required')
    require(bool(c.get('excluded_chip_macs')),'Existing device exclusion list required')
    if c['mode']=='backup':require(c.get('expected_chip_mac'),'Independent expected identity required')
    import serial
    import esptool
    import termios
    with guard_port(c),contextlib.redirect_stdout(sys.stderr):
        s=serial.Serial(port=None,baudrate=115200,timeout=.25,write_timeout=8,exclusive=True)
        s.dtr=False;s.rts=False;s.port=c['port']
        try:
            s.open();attrs=termios.tcgetattr(s.fileno());attrs[2]&=~termios.HUPCL;termios.tcsetattr(s.fileno(),termios.TCSANOW,attrs)
            esp=esptool.ESP32ROM(s,baud=115200);esp.connect(mode='no_reset',attempts=1)
            mac=':'.join(f'{v:02x}' for v in esp.read_mac())
            require(esp.CHIP_NAME=='ESP32' and mac not in c['excluded_chip_macs'],'Wrong/reused device; stop')
            require(not c.get('expected_chip_mac') or mac==c['expected_chip_mac'],'Identity changed; stop')
            require(esp.get_chip_revision()==301 and esp.get_crystal_freq()==40,'Unreviewed silicon/crystal; stop')
            require(not esp.secure_download_mode and not esp.get_secure_boot_enabled() and not esp.get_flash_encryption_enabled() and
                    not esp.get_encrypted_download_disabled(),'Unsupported security; stop')
            # ESP32 ROM does not attach flash itself. Match the SDK no-stub
            # setup, but refuse nondefault eFuse SPI pads rather than guess.
            require(esp.get_chip_spi_pads()==(0,0,0,0,0),'Unreviewed SPI pads; stop')
            esp.flash_spi_attach(0)  # RAM peripheral setup, NOT a flash write.
            require(esptool.cmds.detect_flash_size(esp)=='4MB','Unreviewed geometry; stop')
            info=dict(chip='ESP32',chip_revision=301,crystal_mhz=40,flash_bytes=4194304,flash_size='4MB',expected_chip_mac=mac,
                      secure_boot=False,flash_encryption=False,flash_writes_issued=False,efuse_writes_issued=False,
                      reset_commands=0,esptool_version=esptool.__version__,mode=c['mode'],final_baud=115200)
            if c['mode']=='identify':
                sys.__stdout__.write(json.dumps(info)+'\n');sys.__stdout__.flush();return
            esp=esp.run_stub();esp.change_baud(460800);data=esp.read_flash(0,4194304)
            require(len(data)==4194304,'Incomplete full flash')
            md5=hashlib.md5(data).hexdigest();require(esp.flash_md5sum(0,len(data))==md5,'Independent device MD5 mismatch')
            esp.change_baud(115200)
            require(':'.join(f'{v:02x}' for v in esp.read_mac())==mac and esp.flash_md5sum(0,len(data))==md5,'Restored-baud identity/digest mismatch')
            info.update(verified=True,device_md5=md5,sha256=hashlib.sha256(data).hexdigest(),ram_stub_uploaded=True)
            print('REMOTE_BACKUP_VERIFIED '+json.dumps(info),flush=True)
            sys.__stdout__.buffer.write(data);sys.__stdout__.buffer.flush()
        finally:s.close()


if __name__=='__main__':run(json.load(sys.stdin))
