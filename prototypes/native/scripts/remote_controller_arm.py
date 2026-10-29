#!/usr/bin/env python3
"""One-shot attended Barn USB arming, no reset or live-output command.
Caller MUST hold maintenance lock, create exclusive private journal, and retain
main-OFF isolation. Native serial opens/closes may themselves cause a USB reset;
inspect actual GPIO mode afterward, never assume activation is still deferred.
"""
import json
import sys
import time


def run(config,Device):
    if not all(config.get(k) is True for k in ('apply_confirmed','maintenance_confirmed','equipment_main_power_off','gpio_enable_authorized')):raise ValueError('Explicit isolated GPIO activation approval required')
    wanted=config['manual_profile'];rows=wanted['relays']
    if wanted['hostname']!='barn' or len(rows)!=9 or wanted['timezone']!='America/Los_Angeles' or wanted['clock_source']!='network' or wanted['sensors_enabled'] is not False:raise ValueError('Reviewed Barn test profile required')
    if any(row[k] is not False for row in rows for k in ('value','auto','defaultValue','defaultAuto')):raise ValueError('Every channel must be manual/logical-OFF including boot defaults')
    def emit(stage,**extra):
        sys.__stdout__.write(json.dumps({'stage':stage,**extra})+'\n');sys.__stdout__.flush()
    dev=None
    try:
        dev=Device(config['port'],controller=True)
        def get(route):
            r=dev.request('GET',route)
            if r['status']!=200:raise ValueError('Read rejected, no arming replay')
            return r['data']
        def snapshot():
            s={k:get(route) for k,route in [('ota','/api/ota/status'),('io','/api/io/status'),('config','/api/config'),('edit','/api/profile/edit'),('watchdog','/api/watchdog/status'),('clock','/api/time/status')]}
            ota,io,cfg=s['ota'],s['io'],s['config']
            if not (io['device_id']==config['expected_device_id'] and ota['elf_sha256']==config['expected_elf_sha256'] and ota['healthy'] is True and ota['running_state']=='valid' and ota['uploading'] is False and ota['running_slot']==ota['boot_slot'] and cfg['device_role']=='relay-controller' and cfg['simulated'] is True and cfg['restart_required'] is False and cfg['active_hostname']=='barn' and io['gpio_compiled'] is True and io['gpio_active'] is False and io['armed_for_saved_layout'] is False and io['cleanup_failed'] is False and s['watchdog']['timeout_mask']==0 and s['watchdog']['fault_injection'] is False):raise ValueError('Unexpected identity/boot/selection/health/I-O; no arm issued')
            if s['edit']['profile']!=wanted or s['edit']['boot_id']!=ota['boot_id']:raise ValueError('Test profile/boot changed; no arm issued')
            return s
        first=snapshot();emit('reviewed_preflight',snapshot=first)
        deadline=time.monotonic()+45
        while True:
            c=get('/api/time/status')
            if c.get('timezone_confirmed') is True and c.get('synchronized') is True and c.get('schedule_clock_valid') is True and abs(c['unix_seconds']-time.time())<15:break
            if time.monotonic()>=deadline:raise TimeoutError('Clock not ready; no arm issued')
            time.sleep(1)
        before=snapshot()
        if any(before[k][field]!=first[k][field] for k,field in [('ota','boot_id'),('edit','revision'),('io','layout_hash')]):raise ValueError('Preflight changed; inspect instead of rebasing')
        emit('io_arm_started',snapshot=before)
        reply=dev.command({'op':'io_arm','device_id':config['expected_device_id'],
            'layout_hash':before['io']['layout_hash'],'boot_id':before['ota']['boot_id'],
            'confirm':'enable relay outputs after reboot'})
        if reply['status']!=200 or reply['data'].get('success') is not True:raise ValueError('Arming rejected/uncertain; inspect, no replay')
        emit('io_arm_acknowledged',reply=reply)
        after={k:get(route) for k,route in [('ota','/api/ota/status'),('io','/api/io/status'),('profile','/api/profile')]}
        if after['io']['device_id']!=config['expected_device_id'] or after['io']['armed_for_saved_layout'] is not True or after['profile']!=wanted:raise ValueError('Arming read-back mismatch; no replay/reset')
        if after['ota']['boot_id']!=before['ota']['boot_id'] or after['io']['gpio_active'] is not False:raise ValueError('Unexpected activation/reboot during arm; inspect actual state')
        emit('arm_saved_reboot_required',snapshot=after,reset_command_issued=False,output_commands_issued=False)
    except BaseException as error:
        emit('stopped_inspect_before_any_further_execution',error_type=type(error).__name__)
        raise
    finally:
        if dev is not None:dev.close()
