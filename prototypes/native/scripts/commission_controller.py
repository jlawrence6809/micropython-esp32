#!/usr/bin/env python3
"""Sunroom2 initial provisioning in ONE continuous, attended USB session.
Never arms GPIO, drives relays, resets or reopens the adapter. The hostname change
is deliberately deferred until an operator power cycle with serial tools closed.
A failed/uncertain stage is never automatically replayed. Private inputs/logs
must remain in the unlocked vault. Adapter opening itself can reset hardware.
"""
import argparse
import datetime
import fcntl
import hashlib
import ipaddress
import json
import os
import time
import urllib.request
from pathlib import Path
from usb import Device


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--port',required=True)
    p.add_argument('--maintenance-confirmed',action='store_true',required=True)
    p.add_argument('--loads-disconnected',action='store_true',required=True)
    p.add_argument('--apply',action='store_true',required=True)
    a=p.parse_args();os.umask(0o077);d=a.directory.resolve()
    assert os.path.ismount('/var/lib/private-services') and d.is_relative_to('/var/lib/private-services')
    plan=json.loads((d/'bootstrap-plan.json').read_text())
    backup=json.loads((d/'usb-backup-manifest.json').read_text());assert backup['verified'] is True
    assert hashlib.sha256((d/'original-full-flash.bin').read_bytes()).hexdigest()==backup['sha256']
    expected=plan['expected_chip_mac'].replace(':','')
    profile=json.loads((d/'native-profile.unconfirmed.local.json').read_text())
    assert profile['hostname']=='sunroom2' and len(profile['relays'])==8
    assert profile['timezone'] is None and profile['clock_source']=='manual' and profile['sensors_enabled'] is False
    lock=(d.parent/'usb-maintenance.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    uid=int(os.environ.get('SUDO_UID',os.getuid()));gid=int(os.environ.get('SUDO_GID',os.getgid()))
    def put(path,obj,exclusive=False):
        with path.open('x' if exclusive else 'w') as f:json.dump(obj,f,indent=2);f.write('\n')
        os.chown(path,uid,gid)
    path=d/'commission-initial-journal.local.json'
    journal={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'steps':[],
             'arming_issued':False,'reset_issued':False,'serial_reopens':0,
             'profile_sha256':hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest()}
    put(path,journal,True)  # Refuse an existing journal, even after uncertainty.
    def step(name,fn):
        row={'name':name,'state':'started'};journal['steps'].append(row);put(path,journal)
        result=fn();row['state']='acknowledged';put(path,journal);return result
    def api(method,route,body=''):
        r=dev.request(method,route,body)
        assert r['status']==200,'Non-200 response; inspect without replay'
        return r['data']
    routes=[('config','/api/config'),('io','/api/io/status'),('ota','/api/ota/status'),
            ('watchdog','/api/watchdog/status'),('profile','/api/profile'),('wifi','/api/wifi/status')]
    def check(s):
        io,ota,cfg=s['io'],s['ota'],s['config']
        assert io['device_id']==expected and ota['elf_sha256']==plan['image']['elf_sha256']
        assert cfg['device_role']=='relay-controller' and cfg['simulated'] is True
        assert io['gpio_compiled'] is True and io['gpio_active'] is False
        assert io['armed_for_saved_layout'] is False and io['cleanup_failed'] is False
        assert ota['healthy'] is True and ota['running_state']=='valid' and ota['uploading'] is False
        assert s['watchdog']['fault_injection'] is False and s['watchdog']['timeout_mask']==0
    def snapshot():
        s={k:api('GET',route) for k,route in routes};check(s);return s
    def check_profile(s):
        actual=s['profile'];assert set(actual)==set(profile)
        for key,value in profile.items():
            if key!='relays':assert actual[key]==value,'Scalar/input mismatch'
        assert len(actual['relays'])==8
        for row,wanted in zip(actual['relays'],profile['relays']):
            for key,value in wanted.items():
                if key!='value':assert row[key]==value,'Relay definition mismatch'
    dev=None
    try:
        dev=Device(a.port,controller=True);before=snapshot()
        put(d/'commission-initial-before.local.json',before,True)
        assert before['wifi']['provisioned'] is False,'Existing credentials: inspect, never replay'
        for row in profile['relays']:
            assert api('POST','/api/validate-rule',row['rule'])['success'] is True,'Lua validation failed'
        validated=api('POST','/api/profile/validate',json.dumps(profile));assert validated['success'] is True
        result=step('profile-import',lambda:api('POST','/api/profile/import',json.dumps(profile)))
        assert result['success'] is True and result['outputs_applied'] is True and not result.get('warning')
        saved=snapshot();check_profile(saved);assert saved['io']['layout_hash']==validated['layout_hash']
        put(d/'commission-initial-profile-saved.local.json',saved,True)
        cfg=json.loads((d/'legacy-filesystem/config.json').read_text())['wifi']
        reply=step('provision-private-credentials',lambda:dev.command({'op':'provision','ssid':cfg['ssid'],'password':cfg['password']}))
        assert reply['status']==200 and reply['data']['success'] is True,'Credential completion not confirmed; inspect'
        deadline=time.monotonic()+50
        while time.monotonic()<deadline:
            wifi=api('GET','/api/wifi/status')
            if wifi['provisioned'] and wifi['sta_connected']:break
            time.sleep(1)
        else:raise TimeoutError('Connection not confirmed; do not replay credential mutation')
        after=snapshot();check_profile(after)
        assert after['ota']['boot_id']==before['ota']['boot_id'],'Unexpected reset'
        put(d/'commission-initial-after.local.json',after,True)
        address=ipaddress.IPv4Address(after['wifi']['sta_ip'])
        assert address.is_private and not address.is_loopback and not address.is_link_local
        journal.update(provisioning_confirmed=True,restart_required=after['config']['restart_required'])
        put(path,journal)
    finally:
        if dev is not None:dev.close()
    # GET-only network audit after closing USB. No redirects, proxies or retries.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    network={}
    for key,route in routes:
        with opener.open('http://'+str(address)+route,timeout=4) as response:
            network[key]=json.load(response)
    check(network);check_profile(network)
    put(d/'commission-initial-network.local.json',network,True)
    journal['network_after_usb_close_confirmed']=True;put(path,journal)
    print('Single-session restore confirmed: 8 reviewed relays, private Wi-Fi connected, healthy expected controller, GPIO inactive/unarmed; network audit passed after USB closed. Hostname activation/clock confirmation remain separate.')


if __name__=='__main__':main()
