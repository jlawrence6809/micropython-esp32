#!/usr/bin/env python3
"""Offline only: fake transport, no network/USB/flash."""
import copy
import unittest
from unittest.mock import Mock, patch
import controller_ota as ota
from test_controller_release import fixture, snapshot

DEVICE='123456abcdef'

def state(updated=False):
    s=snapshot(False)
    s['edit']['profile']={'format_version':1,'hostname':'unit','timezone':'America/Los_Angeles',
        'clock_source':'network','schedule_policy':'edge_no_catchup','sensors_enabled':False,
        'sensor_pins':{},'relays':[{'pin':4,'label':'test','rule':'return nil','value':True,
        'auto':True,'isInverted':False,'defaultValue':False,'defaultAuto':False}]}
    s['wifi']={'provisioned':True,'sta_connected':True}
    s['clock']={'timezone':'America/Los_Angeles','synchronized':True,'schedule_clock_valid':True}
    if updated:
        s['ota'].update(elf_sha256=ota.image_info(fixture())['elf_sha256'],boot_id='f'*16,running_slot='ota_1',boot_slot='ota_1')
        s['edit'].update(s['ota']);s['edit']['revision']='1'*64
        s['edit']['profile']['relays'][0].update(auto=False,value=False)
        s['fence']['fence']='2'*64
    return s

class Fake:
    def __init__(self,mode='ok'):
        self.before=state();self.after=state(True);self.mode=mode;self.uploads=[];self.gets=[];self.updated=False
    def get(self,path):
        self.gets.append(path)
        key=dict((route,k) for k,route in ota.ROUTES)[path]
        s=self.after if self.updated else self.before
        return copy.deepcopy(s[key])
    def upload(self,image,digest,fence):
        self.uploads.append((image,digest,fence))
        if self.mode=='reject':return 409,{'success':False}
        self.updated=self.mode!='no_boot'
        if self.mode=='lost_reply':raise TimeoutError('reply lost after commit')
        return 200,{'success':True}

class Tests(unittest.TestCase):
    def run_update(self,fake,lights_only=False,isolated_power_off=False,all_relays_off=False):
        self.journal={};self.saves=[];ticks=iter(range(1000))
        return ota.execute(fake,fixture(),DEVICE,self.journal,
            lambda:self.saves.append(copy.deepcopy(self.journal)),timeout=4,pause=lambda _:None,now=lambda:next(ticks),lights_only=lights_only,isolated_power_off=isolated_power_off,all_relays_off=all_relays_off)
    def test_success_and_fence(self):
        f=Fake();result=self.run_update(f)
        self.assertTrue(result['confirmed']);self.assertFalse(result['gpio_active'])
        self.assertEqual(len(f.uploads),1);self.assertEqual(f.uploads[0][1],ota.image_info(fixture())['image_sha256'])
        self.assertEqual(f.uploads[0][2],f.before['fence']['fence'])
        self.assertEqual(self.journal['state'],'confirmed')
        self.assertEqual(next(x for x in self.saves if x['state']=='upload_started')['upload_attempts'],1)
    def test_lost_reply_inspected_not_replayed(self):
        f=Fake('lost_reply');self.assertTrue(self.run_update(f)['confirmed'])
        self.assertEqual(len(f.uploads),1);self.assertEqual(self.journal['upload_error_type'],'TimeoutError')
    def test_rejection_no_retry(self):
        f=Fake('reject')
        with self.assertRaisesRegex(ValueError,'rejected'):self.run_update(f)
        self.assertEqual(len(f.uploads),1)
    def test_no_boot_no_retry(self):
        f=Fake('no_boot')
        with self.assertRaises(TimeoutError):self.run_update(f)
        self.assertEqual(len(f.uploads),1)
    def test_rollback_observed_no_retry(self):
        f=Fake();f.after['ota'].update(elf_sha256=f.before['ota']['elf_sha256'],boot_id='f'*16,update_state='aborted')
        with self.assertRaisesRegex(RuntimeError,'Old valid image'):self.run_update(f)
        self.assertEqual(len(f.uploads),1);self.assertEqual(self.journal['state'],'rollback_observed')
    def test_active_controller_refused(self):
        f=Fake();f.before=snapshot(True);f.before['wifi']={};f.before['clock']={}
        with self.assertRaisesRegex(ValueError,'UNARMED'):self.run_update(f)
        self.assertEqual(f.uploads,[])
    def lights_fake(self,mode='ok'):
        f=Fake(mode)
        for s in (f.before,f.after):
            s['io'].update(gpio_active=True,armed_for_saved_layout=True)
            s['config']['simulated']=False
        return f
    def all_off_fake(self,mode='ok'):
        f=self.lights_fake(mode)
        for s in (f.before,f.after):
            for row in s['edit']['profile']['relays']:row.update(value=False,auto=False,defaultValue=False,defaultAuto=False)
        return f
    def test_all_off_active_update(self):
        f=self.all_off_fake();self.assertTrue(self.run_update(f,all_relays_off=True)['gpio_active'])
        self.assertEqual(self.journal['execution_policy'],'attended_all_relays_manual_and_startup_off');self.assertEqual(len(f.uploads),1)
    def test_all_off_rejects_each_live_or_default_on(self):
        for key in ['value','auto','defaultValue','defaultAuto']:
            f=self.all_off_fake();f.before['edit']['profile']['relays'][0][key]=True
            with self.assertRaisesRegex(ValueError,'must be OFF'):self.run_update(f,all_relays_off=True)
            self.assertFalse(f.uploads)
    def test_all_off_postboot_on_refused(self):
        f=self.all_off_fake();f.after['edit']['profile']['relays'][0]['value']=True
        with self.assertRaisesRegex(ValueError,'must be OFF'):self.run_update(f,all_relays_off=True)
        self.assertEqual(len(f.uploads),1)
    def test_all_off_lost_reply_never_replays(self):
        f=self.all_off_fake('lost_reply');self.assertTrue(self.run_update(f,all_relays_off=True)['confirmed']);self.assertEqual(len(f.uploads),1)
    def test_all_off_pending_disarm_refused(self):
        f=self.all_off_fake();f.before['io']['armed_for_saved_layout']=False
        with self.assertRaises(ValueError):self.run_update(f,all_relays_off=True)
        self.assertFalse(f.uploads)
    def test_all_off_conflicts_before_network(self):
        f=self.all_off_fake()
        with self.assertRaisesRegex(ValueError,'Choose'):self.run_update(f,lights_only=True,all_relays_off=True)
        self.assertFalse(f.gets)
    def test_all_off_does_not_relax_identity(self):
        f=self.all_off_fake();f.before['io']['device_id']='0'*12
        with self.assertRaises(ValueError):self.run_update(f,all_relays_off=True)
        self.assertFalse(f.uploads)
    def test_explicit_lights_active_update(self):
        f=self.lights_fake();self.assertTrue(self.run_update(f,True)['gpio_active'])
        self.assertEqual(len(f.uploads),1)
        self.assertEqual(self.journal['execution_policy'],'explicit_lights_only_remote_reboot')
    def test_lights_lost_reply_never_replayed(self):
        f=self.lights_fake('lost_reply');self.assertTrue(self.run_update(f,True)['confirmed'])
        self.assertEqual(len(f.uploads),1)
    def test_lights_pending_disarm_still_refused(self):
        f=self.lights_fake();f.before['io']['armed_for_saved_layout']=False
        with self.assertRaises(ValueError):self.run_update(f,True)
        self.assertEqual(f.uploads,[])
    def test_lights_activation_loss_refused_after_update(self):
        f=self.lights_fake();f.after['io'].update(gpio_active=False,armed_for_saved_layout=False);f.after['config']['simulated']=True
        with self.assertRaisesRegex(ValueError,'activation changed'):self.run_update(f,True)
        self.assertEqual(len(f.uploads),1)
    def test_lights_policy_does_not_relax_identity_or_configuration(self):
        f=self.lights_fake();f.before['io']['device_id']='0'*12
        with self.assertRaises(ValueError):self.run_update(f,True)
        self.assertEqual(f.uploads,[])
        f=self.lights_fake();f.after['edit']['profile']['relays'][0]['label']='changed'
        with self.assertRaisesRegex(ValueError,'Configuration changed'):self.run_update(f,True)
        self.assertEqual(len(f.uploads),1)
    def test_isolated_unarmed_remote_success(self):
        f=Fake();self.assertTrue(self.run_update(f,isolated_power_off=True)['confirmed'])
        self.assertFalse(self.journal['after']['io']['gpio_active'])
        self.assertEqual(self.journal['execution_policy'],'isolated_unarmed_remote_reboot')
        self.assertEqual(len(f.uploads),1)
    def test_isolated_policy_still_refuses_active(self):
        f=self.lights_fake()
        with self.assertRaisesRegex(ValueError,'UNARMED'):self.run_update(f,isolated_power_off=True)
        self.assertEqual(f.uploads,[])
    def test_isolated_lost_reply_inspect_no_replay(self):
        f=Fake('lost_reply');self.assertTrue(self.run_update(f,isolated_power_off=True)['confirmed'])
        self.assertEqual(len(f.uploads),1)
    def test_conflicting_policies_before_network(self):
        f=Fake()
        with self.assertRaisesRegex(ValueError,'Choose'):self.run_update(f,True,True)
        self.assertEqual(f.gets,[]);self.assertEqual(f.uploads,[])
    def test_pending_arm_refused(self):
        f=Fake();f.before['io']['armed_for_saved_layout']=True
        with self.assertRaises(ValueError):self.run_update(f)
        self.assertEqual(f.uploads,[])
    def test_wrong_identity_and_noop(self):
        for field in ['identity','noop']:
            f=Fake()
            if field=='identity':f.before['io']['device_id']='0'*12
            else:
                f.before['ota']['elf_sha256']=ota.image_info(fixture())['elf_sha256']
                f.before['edit']['elf_sha256']=f.before['ota']['elf_sha256']
            with self.assertRaises(ValueError):self.run_update(f)
            self.assertEqual(f.uploads,[])
    def test_corrupt_image_before_network(self):
        f=Fake()
        with self.assertRaises(ValueError):ota.execute(f,b'bad',DEVICE,{},lambda:None)
        self.assertEqual(f.gets,[]);self.assertEqual(f.uploads,[])
    def test_changed_preflight_refused(self):
        f=Fake();original=f.get
        def get(path):
            data=original(path)
            if len(f.gets)>len(ota.ROUTES) and path=='/api/profile/edit':data['revision']='f'*64
            return data
        f.get=get
        with self.assertRaisesRegex(ValueError,'changed'):self.run_update(f)
        self.assertEqual(f.uploads,[])
    def test_configuration_change_after_upload_refused(self):
        f=Fake();f.after['edit']['profile']['relays'][0]['rule']='return true'
        with self.assertRaisesRegex(ValueError,'Configuration changed'):self.run_update(f)
        self.assertEqual(len(f.uploads),1)
    def test_wrong_slot_layout_or_activation_refused(self):
        for kind in ['slot','layout','activation']:
            f=Fake()
            if kind=='slot':f.after['ota'].update(running_slot='ota_0',boot_slot='ota_0')
            if kind=='layout':f.after['io']['layout_hash']='f'*64
            if kind=='activation':f.after['io']['gpio_active']=True
            with self.assertRaises(ValueError):self.run_update(f)
            self.assertEqual(len(f.uploads),1)
    def test_preflight_get_error_no_upload(self):
        f=Fake();f.get=Mock(side_effect=TimeoutError())
        with self.assertRaises(TimeoutError):self.run_update(f)
        self.assertEqual(f.get.call_count,1);self.assertEqual(f.uploads,[])
    def test_clock_not_synced_no_upload_replay(self):
        f=Fake();f.after['clock'].update(synchronized=False,schedule_clock_valid=False)
        with self.assertRaisesRegex(ValueError,'clock sync'):self.run_update(f)
        self.assertEqual(len(f.uploads),1)
    def test_redirects_disabled_and_lan_required(self):
        self.assertIsNone(ota.NoRedirect().redirect_request(None,None,302,'',{},'http://other'))
        for host in ['127.0.0.1','8.8.8.8','http://192.168.1.1','169.254.1.2','0.0.0.0']:
            with self.assertRaises(ValueError):ota.Transport(host)
    def test_transport_upload_headers_single_call(self):
        t=ota.Transport('192.168.1.2');response=Mock();response.status=200;response.read.return_value=b'{"success":true}'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        t.opener=Mock();t.opener.open.return_value=response
        self.assertEqual(t.upload(b'abc','a'*64,'b'*64),(200,{'success':True}))
        request=t.opener.open.call_args.args[0]
        self.assertEqual(request.get_method(),'POST');self.assertEqual(request.get_header('X-firmware-sha256'),'a'*64)
        self.assertEqual(request.get_header('X-garden-ota-fence'),'b'*64);self.assertEqual(t.opener.open.call_count,1)

if __name__=='__main__':unittest.main()
