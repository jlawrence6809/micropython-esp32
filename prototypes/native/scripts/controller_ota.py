#!/usr/bin/env python3
"""Guarded LAN OTA: unarmed default, explicit lights-only or attended all-OFF opt-in.
Default is GET-only audit. --apply uploads ONCE, journals uncertainty, and verifies
new boot/slot/image/configuration/clock. Never arm, reset via USB, rebase a stale
fence, retry an upload, restore settings or fall back to bench/unfenced updates.
Target identities, profiles, tokens and execution journals stay in the vault.
"""
import argparse
import copy
import datetime
import fcntl
import hashlib
import ipaddress
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from controller_release import controller_state, image_info, require, validate_snapshot, validate_image_target

ROUTES=(('ota','/api/ota/status'),('config','/api/config'),('io','/api/io/status'),
        ('watchdog','/api/watchdog/status'),('edit','/api/profile/edit'),('fence','/api/ota/fence'),
        ('wifi','/api/wifi/status'),('clock','/api/time/status'))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class Transport:
    def __init__(self,host):
        address=ipaddress.IPv4Address(host)
        require(address.is_private and not (address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast),'Private LAN IPv4 required')
        self.base='http://'+str(address)
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def get(self,path):
        with self.opener.open(self.base+path,timeout=4) as response:return json.load(response)
    def upload(self,image,digest,fence):
        request=urllib.request.Request(self.base+'/api/ota/upload',data=image,method='POST',headers={
            'Content-Type':'application/octet-stream','X-Firmware-SHA256':digest,'X-Garden-OTA-Fence':fence})
        try:
            with self.opener.open(request,timeout=135) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as error:
            # A malformed/lost reply remains uncertain, never an excuse to replay.
            return error.code,json.load(error)

def snapshot(transport):return {key:transport.get(route) for key,route in ROUTES}

def profile_configuration(profile,boot_defaults=False):
    result=copy.deepcopy(profile)
    for row in result['relays']:
        row.pop('value',None)
        if boot_defaults:row['auto']=row['defaultAuto']
    return result

def unarmed(state):
    require(state['gpio_active'] is False,'Executor supports isolated UNARMED controllers only; active updates remain review-gated')

def require_all_relays_off(s):
    rows=s['edit']['profile']['relays']
    require(bool(rows) and all(row.get(k) is False for row in rows for k in
        ('value','auto','defaultValue','defaultAuto')),'All relay values/AUTO/startup defaults must be OFF')

def prepare(transport,device_id,info,lights_only=False,all_relays_off=False):
    first=snapshot(transport);a=validate_snapshot(first,device_id,info)
    if not (lights_only or all_relays_off):unarmed(a)
    if all_relays_off:require_all_relays_off(first)
    second=snapshot(transport);b=validate_snapshot(second,device_id,info)
    if not (lights_only or all_relays_off):unarmed(b)
    if all_relays_off:require_all_relays_off(second)
    require(a==b,'Controller changed during inspection; no rebase/retry')
    require(profile_configuration(first['edit']['profile'])==profile_configuration(second['edit']['profile']),'Profile changed during inspection')
    require(second['wifi'].get('provisioned') is True and second['wifi'].get('sta_connected') is True,'Wi-Fi not connected/provisioned')
    return second,b

def verify_after(after,before,device_id,info,lights_only=False,all_relays_off=False):
    state=controller_state(after,device_id)
    validate_image_target(after,info)
    if not (lights_only or all_relays_off):unarmed(state)
    if all_relays_off:require_all_relays_off(after)
    require(state['gpio_active'] is before['io']['gpio_active'],'GPIO activation changed across OTA')
    require(after['ota']['elf_sha256']==info['elf_sha256'],'Wrong updated ELF')
    require(after['ota']['boot_id']!=before['ota']['boot_id'],'No new boot')
    require(after['ota']['running_slot']!=before['ota']['running_slot'],'No slot switch')
    require(state['layout_hash']==before['io']['layout_hash'],'Layout changed across OTA')
    require(profile_configuration(after['edit']['profile'])==profile_configuration(before['edit']['profile'],True),'Configuration changed (boot AUTO defaults expected; live values excluded)')
    require(after['wifi'].get('provisioned') is True and after['wifi'].get('sta_connected') is True,'Wi-Fi not restored')
    require(after['clock'].get('timezone')==before['edit']['profile']['timezone'],'Clock timezone not restored')
    return state

def execute(transport,image,device_id,journal,save,timeout=120,pause=time.sleep,now=time.monotonic,lights_only=False,isolated_power_off=False,chip_target='esp32s3',all_relays_off=False):
    require(sum((lights_only,isolated_power_off,all_relays_off))<=1,'Choose exactly one maintenance policy')
    info=image_info(image,chip_target)  # Before any device request.
    before,state=prepare(transport,device_id,info,lights_only,all_relays_off)
    journal['execution_policy']=('attended_all_relays_manual_and_startup_off' if all_relays_off else
        'explicit_lights_only_remote_reboot' if lights_only else
        'isolated_unarmed_remote_reboot' if isolated_power_off else 'attended_bare_unarmed')
    journal.update(state='preflight_passed',image=info,before=before);save()
    journal.update(state='upload_started',upload_attempts=1);save()  # Durable intent BEFORE POST.
    try:
        code,reply=transport.upload(image,info['image_sha256'],state['ota_fence'])
    except (OSError,ValueError) as error:
        journal.update(state='upload_completion_uncertain',upload_error_type=type(error).__name__);save()
    else:
        journal.update(response_status=code,response=reply);save()
        require(code==200 and reply.get('success') is True,'Upload rejected; inspect actual state. No retry/rebase.')
        journal['state']='image_accepted';save()
    # Only GET polling from here; upload is never called again, even after a lost reply.
    deadline=now()+timeout;journal['verification_transport_errors']=[]
    while now()<deadline:
        try:
            ota=transport.get('/api/ota/status')
        except (OSError,ValueError) as error:
            journal['verification_transport_errors'].append(type(error).__name__);save();pause(1);continue
        journal['last_observed_ota']=ota;save()
        if (ota.get('healthy') is True and ota.get('running_state')=='valid' and
            ota.get('elf_sha256')==before['ota']['elf_sha256'] and
            ota.get('boot_id')!=before['ota']['boot_id'] and ota.get('update_state') in ('aborted','invalid')):
            journal['state']='rollback_observed';save()
            raise RuntimeError('Old valid image restored after failed candidate; inspect, no upload replay')
        if (ota.get('healthy') is True and ota.get('running_state')=='valid' and
            ota.get('elf_sha256')==info['elf_sha256'] and ota.get('boot_id')!=before['ota']['boot_id']):break
        pause(1)
    else:raise TimeoutError('New healthy image not confirmed. Inspect journal/device; NEVER replay upload automatically.')
    after=snapshot(transport);verify_after(after,before,device_id,info,lights_only,all_relays_off)
    profile=after['edit']['profile']
    if profile['clock_source']=='network' and profile['timezone'] is not None:
        deadline=now()+30
        while not after['clock'].get('schedule_clock_valid') and now()<deadline:
            pause(1);after['clock']=transport.get('/api/time/status')
        require(after['clock'].get('synchronized') is True and after['clock'].get('schedule_clock_valid') is True,'Image updated, but clock sync not confirmed; inspect, do not repeat upload')
    journal.update(state='confirmed',after=after,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
    return {'confirmed':True,'new_boot':True,'slot_switched':True,'configuration_preserved':True,'gpio_active':after['io']['gpio_active'],'image':info}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',type=Path,required=True,help='Vault JSON: host and independently verified expected_device_id')
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--chip-target',choices=('esp32s3','esp32'),default='esp32s3')
    p.add_argument('--journal',type=Path,help='NEW vault-only journal, mandatory for --apply')
    p.add_argument('--apply',action='store_true')
    p.add_argument('--verification-timeout',type=int,default=120,help='15..600 seconds of GET-only post-upload recovery polling; never retries upload')
    p.add_argument('--maintenance-confirmed',action='store_true')
    p.add_argument('--bare-board-confirmed',action='store_true')
    p.add_argument('--attended-reboot-confirmed',action='store_true')
    p.add_argument('--equipment-power-off-confirmed',action='store_true',help='Operator confirms equipment power OFF/disconnected and controller UNARMED on its reviewed maintenance supply; attached wiring need not be called bare')
    p.add_argument('--lights-only-confirmed',action='store_true',help='Operator explicitly confirms ONLY lights connected, no power equipment; permits armed OTA')
    p.add_argument('--all-relays-off-confirmed',action='store_true',help='Attended attached-load OTA; every current value/AUTO/boot default must be OFF before and after, activation unchanged')
    p.add_argument('--remote-reboot-confirmed',action='store_true',help='Operator accepts maintenance reboot, boot defaults and possible physical recovery if remote OTA fails')
    a=p.parse_args();os.umask(0o077)
    require(15<=a.verification_timeout<=600,'Verification timeout must be 15..600 seconds')
    lights_only=a.lights_only_confirmed
    isolated_power_off=a.equipment_power_off_confirmed
    all_relays_off=a.all_relays_off_confirmed
    require(sum((lights_only,isolated_power_off,all_relays_off))<=1,'Choose exactly one maintenance policy')
    require((lights_only or isolated_power_off or all_relays_off)==a.remote_reboot_confirmed,'Explicit alternative-policy and remote-reboot acknowledgements required together')
    require(os.path.ismount('/var/lib/private-services'),'Unlocked vault required')
    require(a.target.resolve().is_relative_to('/var/lib/private-services'),'Target identity must stay in vault')
    target=json.loads(a.target.read_text())
    require(target.get('chip_target','esp32s3')==a.chip_target,'Private target file/selected chip target mismatch')
    image=a.image.read_bytes();info=image_info(image,a.chip_target)
    transport=Transport(target['host']);device_id=target['expected_device_id']
    if not a.apply:
        _,state=prepare(transport,device_id,info,lights_only,all_relays_off)
        print(json.dumps({'audit_passed':True,'upload_issued':False,'gpio_active':state['gpio_active'],'image':info}));return
    require(a.maintenance_confirmed and (lights_only or isolated_power_off or all_relays_off or (a.bare_board_confirmed and a.attended_reboot_confirmed)),'Attended bare-board OR isolated-unarmed/lights-only/all-OFF remote maintenance acknowledgements required')
    require(a.journal is not None and a.journal.resolve().is_relative_to('/var/lib/private-services'),'New vault journal required')
    lock=(a.journal.parent.parent/'usb-maintenance.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    journal={'state':'starting','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'upload_attempts':0,'arming_issued':False,'usb_opened':False}
    # Never overwrite/reuse a journal, including one left by uncertainty or failure.
    with a.journal.open('x') as f:json.dump(journal,f)
    def save():
        tmp=a.journal.with_suffix('.tmp');tmp.write_text(json.dumps(journal,indent=2)+'\n');tmp.replace(a.journal)
    try:result=execute(transport,image,device_id,journal,save,timeout=a.verification_timeout,lights_only=lights_only,isolated_power_off=isolated_power_off,chip_target=a.chip_target,all_relays_off=all_relays_off)
    except Exception:
        journal['inspection_required']=True;save();raise
    print(json.dumps(result,indent=2))  # No private identities/config/fence tokens.

if __name__=='__main__':main()
