#!/usr/bin/env python3
"""One attended unarmed Relay_X8 Wi-Fi provision, then bounded GET-only LAN checks.
Credentials arrive only via SSH stdin; never print/log request or password. Caller
captures lifecycle/snapshots directly in mounted encrypted vault. No reset/arm/
profile edits, proxies, redirects or provision replay. Stop on uncertainty.
"""
import contextlib
import ipaddress
import json
import sys
import time
import urllib.request
from remote_relay_x8_bootstrap import guard_port, require
from controller_release import controller_state, validate_image_target


def validate(c):
    require(c.get('purpose')=='relay-x8-private-wifi-provision' and c.get('apply_confirmed') is True and
            c.get('loads_disconnected') is True,'Attended unloaded provisioning required')
    require(isinstance(c.get('approved_ssid'),str) and bool(c['approved_ssid']) and
            c['wifi']['ssid']==c['approved_ssid'] and isinstance(c['wifi']['password'],str) and
            8<=len(c['wifi']['password'].encode())<=63,'Reviewed saved network credential required')
    require(c['expected_image']['chip_target']=='esp32','Original ESP32 only')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def run(c):
    validate(c)
    import serial
    from usb import Device, prevent_linux_hangup_reset
    def emit(stage,**more):
        sys.__stdout__.write(json.dumps(dict(stage=stage,**more))+'\n');sys.__stdout__.flush()
    try:
        with guard_port(c),contextlib.redirect_stdout(sys.stderr):
            s=serial.Serial(port=None,baudrate=115200,timeout=.25,write_timeout=8,exclusive=True)
            s.dtr=False;s.rts=False;s.port=c['port']
            try:
                s.open();prevent_linux_hangup_reset(s);dev=Device.__new__(Device);dev.serial=s;dev.sequence=0
                def get(route):
                    rep=dev.request('GET',route);require(rep['status']==200,'GET rejected');return rep['data']
                routes=[('config','/api/config'),('io','/api/io/status'),('ota','/api/ota/status'),
                        ('watchdog','/api/watchdog/status'),('edit','/api/profile/edit'),('fence','/api/ota/fence')]
                snap={k:get(p) for k,p in routes};state=controller_state(snap,c['expected_device_id'])
                validate_image_target(snap,c['expected_image'])
                require(state['gpio_active'] is False and state['boot_id']==c['expected_boot_id'] and
                        state['running_elf']==c['expected_image']['elf_sha256'],'Identity/boot/activation changed')
                require(get('/api/profile')==c['expected_profile'] and state['revision']==c['expected_revision'],'Profile changed; no provision')
                require(get('/api/wifi/status')['provisioned'] is False,'Existing credentials; inspect, never replay')
                emit('preflight_verified_unarmed')
                emit('credential_provision_started');started=time.monotonic()
                reply=dev.command(dict(op='provision',ssid=c['wifi']['ssid'],password=c['wifi']['password']))
                require(reply['status']==200 and reply['data']['success'] is True,'Provision not acknowledged; inspect no replay')
                emit('credential_provision_acknowledged')
                c['wifi'].pop('password',None)  # No longer needed for GET-only observation.
                deadline=started+65
                while time.monotonic()<deadline:
                    wifi=get('/api/wifi/status')
                    if wifi['provisioned'] and wifi['sta_connected'] and wifi.get('sta_ip'):break
                    time.sleep(1)
                else:raise ValueError('Credentials saved but no DHCP observed; no provision replay')
                require(wifi['sta_ssid']==c['wifi']['ssid'],'Unexpected associated network')
                io=get('/api/io/status');ota=get('/api/ota/status')
                require(io['gpio_active'] is False and io['armed_for_saved_layout'] is False and
                        ota['boot_id']==state['boot_id'] and ota['healthy'] and ota['running_state']=='valid','State changed during association')
                emit('dhcp_observed',seconds=time.monotonic()-started,wifi=wifi)
            finally:s.close();emit('serial_closed')
        # Port released before LAN observation. All further operations GET-only.
        address=ipaddress.ip_address(wifi['sta_ip'])
        require(isinstance(address,ipaddress.IPv4Address) and any(address in ipaddress.ip_network(net) for net in
                ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')),'Expected literal private LAN IPv4')
        base='http://'+str(address);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        def lan(route):
            with opener.open(base+route,timeout=5) as response:return json.load(response)
        start=time.monotonic();samples=[]
        for delay in [0,15,30,60,120,180,240,300]:
            time.sleep(max(0,start+delay-time.monotonic()))
            snap={k:lan(p) for k,p in routes};state=controller_state(snap,c['expected_device_id']);validate_image_target(snap,c['expected_image'])
            current=lan('/api/wifi/status');profile=lan('/api/profile')
            require(state['gpio_active'] is False and state['boot_id']==c['expected_boot_id'] and
                    state['running_elf']==c['expected_image']['elf_sha256'] and profile==c['expected_profile'] and
                    current['sta_connected'] is True and current['sta_ssid']==c['wifi']['ssid'] and
                    current['sta_ip']==str(address),'LAN identity/config/connection changed')
            sample=dict(seconds=time.monotonic()-start,wifi=current,status=lan('/api/status'),state=state)
            samples.append(sample);emit('lan_sample',sample=sample)
        emit('wifi_bench_passed',host=str(address),samples=samples,arming_issued=False,reset_commands=0,
             provision_requests=1,profile_unchanged=True,seconds=time.monotonic()-start)
    except BaseException as ex:
        emit('stopped_inspect_no_replay',error_type=type(ex).__name__);raise


if __name__=='__main__':run(json.load(sys.stdin))
