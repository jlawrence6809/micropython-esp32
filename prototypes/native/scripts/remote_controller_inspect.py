#!/usr/bin/env python3
"""GET-only bounded serial inspector; run via SSH stdin, capture output in vault.
Caller supplies run(config, Device, prevent_linux_hangup_reset). No reset/flash,
profile import, credential provision or arming. Opening the adapter itself may
reset hardware and requires attended isolated maintenance approval.
"""
import json
import sys
import time


def run(config, Device, prevent_linux_hangup_reset):
    import serial
    if config.get('maintenance_confirmed') is not True:
        raise ValueError('Maintenance acknowledgement required')
    s=serial.Serial(port=None,baudrate=115200,timeout=.25,exclusive=True)
    s.dtr=False;s.rts=False;s.port=config['port']
    result={'get_only':True,'arming_issued':False,'reset_issued':False,'snapshot':{}}
    try:
        s.open();prevent_linux_hangup_reset(s)
        data=bytearray();end=time.monotonic()+3
        while time.monotonic()<end:
            data.extend(s.read(4096))
            if len(data)>131072:raise RuntimeError('UART capture bound exceeded')
        sys.stderr.buffer.write(b'PASSIVE_CAPTURE_BEGIN\n'+data+b'\nPASSIVE_CAPTURE_END\n')
        sys.stderr.flush()
        result['rom_download_seen']=b'waiting for download' in data
        dev=Device.__new__(Device);dev.serial=s;dev.sequence=0
        for key,route in [('config','/api/config'),('io','/api/io/status'),('ota','/api/ota/status'),('watchdog','/api/watchdog/status'),('profile','/api/profile'),('wifi','/api/wifi/status'),('clock','/api/time/status')]:
            reply=dev.request('GET',route)
            if reply['status']!=200:raise ValueError('Read-only API rejected')
            result['snapshot'][key]=reply['data']
        result['read_complete']=True
    except Exception as error:
        result.update(read_complete=False,error_type=type(error).__name__)
    finally:
        s.close()
    print(json.dumps(result),flush=True)
