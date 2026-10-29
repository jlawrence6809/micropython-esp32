#!/usr/bin/env python3
"""Attended UNARMED UART profile/control tests. No reset, credentials or arming.
Only use with fresh owner-only vault journal. Mutation requests issued ONCE;
uncertain completion stops, never retries/restores automatically. All defaults OFF.
"""
import contextlib
import copy
import json
import sys
import time
from remote_relay_x8_bootstrap import guard_port, require


def validate(c):
    require(c.get('purpose')=='relay-x8-unarmed-memory-test' and c.get('loads_disconnected') is True and
            c.get('apply_confirmed') is True, 'Explicit unloaded memory-only test required')
    p=c['profile'];pins=[32,33,25,26,27,14,12,13]
    hostname=c.get('reviewed_hostname','relay-x8-bench')
    require(hostname in ('relay-x8-bench','relay-x8-spare') and p['hostname']==hostname and p['clock_source']=='manual' and p['timezone'] is None and
            p['sensors_enabled'] is False and all(v==-1 for v in p['sensor_pins'].values()), 'Inert board profile required')
    require([r['pin'] for r in p['relays']]==pins and [r['label'] for r in p['relays']]==['K'+str(i) for i in range(1,9)], 'Exact Relay_X8 map required')
    require(all(r['rule']=='return nil' and all(r[k] is False for k in ['auto','value','defaultAuto','defaultValue','isInverted']) for r in p['relays']), 'All channels/defaults/AUTO must be OFF')


def run(c):
    validate(c)
    import serial
    from usb import Device, prevent_linux_hangup_reset
    def emit(stage,**more):
        sys.__stdout__.write(json.dumps(dict(stage=stage,**more))+'\n');sys.__stdout__.flush()
    with guard_port(c),contextlib.redirect_stdout(sys.stderr):
        s=serial.Serial(port=None,baudrate=115200,timeout=.25,write_timeout=8,exclusive=True)
        s.dtr=False;s.rts=False;s.port=c['port']
        try:
            s.open();prevent_linux_hangup_reset(s);dev=Device.__new__(Device);dev.serial=s;dev.sequence=0
            def get(route):
                rep=dev.request('GET',route);require(rep['status']==200,'GET rejected');return rep['data']
            def guard():
                io=get('/api/io/status');ota=get('/api/ota/status')
                require(io['device_id']==c['expected_device_id'] and io['gpio_active'] is False and
                        io['armed_for_saved_layout'] is False and not io.get('persistence_uncertain') and
                        io.get('outputs_applied') is not False,'Identity/activation/persistence changed; stop')
                require(ota['boot_id']==c['expected_boot_id'] and ota['elf_sha256']==c['expected_elf'] and
                        ota['chip_target']=='esp32' and ota['healthy'] is True and ota['running_state']=='valid' and
                        not ota['uploading'],'Boot/health changed; stop')
                return io,ota
            def once(name,route,body,status=200):
                guard();emit(name+'_started')
                rep=dev.request('POST',route,body if isinstance(body,str) else json.dumps(body,separators=(',',':')))
                require(rep['status']==status,'POST rejected; inspect no replay')
                emit(name+'_completed');guard();return rep['data']
            def rows():return get('/api/profile')['relays']
            guard();edit=get('/api/profile/edit')
            require(edit['revision']==c['expected_revision'],'Initial revision changed; no import')
            require(len(rows())==1 and rows()[0]['pin']==4,'Not reviewed factory profile; no import')
            for name,rule,success in [('true','return true',True),('false','return false',True),('hold','return nil',True),
                                      ('syntax','return (',False),('runaway','while true do end',False),
                                      ('sandbox','return os.execute("x")',False),('result','return 1',False),('length','x'*2049,False)]:
                result=once('validate_'+name,'/api/validate-rule',rule)
                require(result['success'] is success,'Unexpected Lua validation result')
            require(get('/api/profile/edit')['revision']==c['expected_revision'],'Validation changed profile')
            once('profile_validate','/api/profile/validate',c['profile'])
            bad=copy.deepcopy(c['profile']);bad['relays'][0]['pin']=1
            once('reject_uart_pin','/api/profile/validate',bad,400)
            bad=copy.deepcopy(c['profile']);bad['relays'][1]['pin']=32
            once('reject_duplicate_pin','/api/profile/validate',bad,400)
            once('profile_import','/api/profile/import',c['profile'])
            require([r['pin'] for r in rows()]==[r['pin'] for r in c['profile']['relays']],'Import map mismatch')
            for target in c['profile']['relays']:
                label=target['label']
                for state in (True,False):
                    once('manual_'+label+('_on' if state else '_off'),'/api/relays/control',dict(label=label,state=state))
                    for r in rows():
                        require(r['value'] is (state if r['label']==label else False) and r['auto'] is False and
                                r['defaultValue'] is False and r['defaultAuto'] is False,'Manual/isolation/default mismatch')
            def patch(name,changes):
                e=get('/api/profile/edit')
                return once(name,'/api/profile/patch',dict(expected_revision=e['revision'],expected_boot_id=c['expected_boot_id'],changes=changes))
            patch('auto_enable',dict(relay_update=dict(pin=32,label='K1',changes=dict(rule='return true',auto=True))))
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                if rows()[0]['value'] is True:break
                time.sleep(.2)
            else:raise ValueError('Memory automation did not evaluate')
            once('manual_disables_auto','/api/relays/control',dict(label='K1',state=False));time.sleep(.8)
            require(rows()[0]['value'] is False and rows()[0]['auto'] is False,'Manual OFF failed to disable AUTO')
            patch('restore_inert_rule',dict(relay_update=dict(pin=32,label='K1',changes=dict(rule='return nil',auto=False))))
            p=get('/api/profile');require(p==c['profile'],'Final inert profile differs from imported template')
            cfg=get('/api/config');io,ota=guard();wd=get('/api/watchdog/status');wifi=get('/api/wifi/status')
            require(wd['timeout_mask']==0 and wd['fault_injection'] is False and wifi['provisioned'] is False,'Watchdog/Wi-Fi state changed')
            emit('memory_tests_passed',manual_pairs=8,lua_cases=8,auto_manual_override=True,
                 final_all_off=True,arming_issued=False,reset_commands=0,hostname_restart_required=cfg['restart_required'],
                 snapshot=dict(config=cfg,io=io,ota=ota,watchdog=wd,wifi=wifi,profile=p,status=get('/api/status')))
        except BaseException as ex:
            emit('stopped_inspect_no_replay',error_type=type(ex).__name__);raise
        finally:s.close();emit('serial_closed')


if __name__=='__main__':run(json.load(sys.stdin))
