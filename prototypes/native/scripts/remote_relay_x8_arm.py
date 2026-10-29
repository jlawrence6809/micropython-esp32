#!/usr/bin/env python3
"""One-shot attended original-ESP32 Relay_X8 all-OFF arming; no reboot/ON command.
Caller retains fresh private journal and unloaded/operator-present approval. The
pending arm must be activated only by separately attended EN boot, never OTA.
"""
import contextlib
import json
import sys
import time
from remote_relay_x8_bootstrap import guard_port, require
from controller_release import controller_state, validate_image_target


def validate(c):
    require(c.get('purpose')=='relay-x8-attended-unloaded-arm' and all(c.get(k) is True for k in
            ['apply_confirmed','loads_disconnected','operator_present','gpio_enable_authorized']), 'Explicit attended unloaded activation approval required')
    p=c['profile']
    require(p['hostname']=='relay-x8-bench' and p['timezone']=='America/Los_Angeles' and p['clock_source']=='network' and
            p['sensors_enabled'] is False and all(v==-1 for v in p['sensor_pins'].values()), 'Reviewed board/clock/sensors required')
    require([r['pin'] for r in p['relays']]==[32,33,25,26,27,14,12,13] and
            [r['label'] for r in p['relays']]==['K'+str(i) for i in range(1,9)], 'Exact reviewed map required')
    require(all(r['rule']=='return nil' and all(r[k] is False for k in ['value','auto','defaultValue','defaultAuto','isInverted']) for r in p['relays']), 'All8 must be manual/current/default OFF, active-high')
    require(c['image']['chip_target']=='esp32','Original ESP32 required')


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
            def snapshot():
                routes=[('config','/api/config'),('io','/api/io/status'),('ota','/api/ota/status'),('watchdog','/api/watchdog/status'),
                        ('edit','/api/profile/edit'),('fence','/api/ota/fence'),('clock','/api/time/status')]
                snap={k:get(p) for k,p in routes};state=controller_state(snap,c['expected_device_id']);validate_image_target(snap,c['image'])
                require(state['gpio_active'] is False and state['boot_id']==c['expected_boot_id'] and
                        state['running_elf']==c['image']['elf_sha256'] and state['layout_hash']==c['expected_layout_hash'] and
                        state['revision']==c['expected_revision'],'Reviewed identity/activation/layout/revision changed; no arm')
                require(snap['edit']['profile']==c['profile'] and snap['config']['hostname']=='relay-x8-bench' and
                        snap['config']['active_hostname']=='relay-x8-bench','Reviewed all-OFF profile/hostname changed; no arm')
                clock=snap['clock'];require(clock.get('timezone')=='America/Los_Angeles' and
                        clock.get('timezone_confirmed') is True and clock.get('synchronized') is True and
                        clock.get('schedule_clock_valid') is True and abs(clock['unix_seconds']-time.time())<15,'Clock not ready; no arm')
                return snap,state
            first,a=snapshot();before,b=snapshot();require(a==b,'Preflight changed; no rebase/arm')
            emit('reviewed_all_off_preflight',snapshot=before)
            emit('io_arm_started')
            reply=dev.command(dict(op='io_arm',device_id=c['expected_device_id'],layout_hash=b['layout_hash'],
                                   boot_id=b['boot_id'],confirm='enable relay outputs after reboot'))
            require(reply['status']==200 and reply['data'].get('success') is True,'Arm not acknowledged; inspect no replay')
            emit('io_arm_acknowledged')
            after={k:get(p) for k,p in [('io','/api/io/status'),('ota','/api/ota/status'),('profile','/api/profile')]}
            require(after['io']['device_id']==c['expected_device_id'] and after['io']['layout_hash']==b['layout_hash'] and
                    after['io']['armed_for_saved_layout'] is True and after['io']['gpio_active'] is False and
                    after['ota']['boot_id']==b['boot_id'] and after['ota']['elf_sha256']==c['image']['elf_sha256'] and
                    after['profile']==c['profile'],'Arming readback/reboot mismatch; inspect, no replay/reset')
            emit('arm_saved_waiting_operator_en',snapshot=after,reset_commands=0,relay_control_commands=0)
        except BaseException as ex:
            emit('stopped_inspect_no_replay',error_type=type(ex).__name__);raise
        finally:s.close();emit('serial_closed')


if __name__=='__main__':run(json.load(sys.stdin))
