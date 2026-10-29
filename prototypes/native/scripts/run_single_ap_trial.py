#!/usr/bin/env python3
"""One-shot approved Sunroom experiment. No upload replay, vault-only evidence.
Default refuses mutation; explicit approved isolated/capture flags required.
"""
import argparse,datetime,hashlib,importlib.util,json,os,shlex,struct,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from controller_ota import Transport,snapshot

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--isolated-unarmed-confirmed',action='store_true');p.add_argument('--capture-tools-authorized',action='store_true');p.add_argument('--run-id',default='single-ap');p.add_argument('--observer-config',type=Path,required=True,help='Vault-only approved observer_host/workstation/key/known_hosts JSON');a=p.parse_args();assert a.run_id.replace('-','').isalnum()
 if not(a.apply and a.isolated_unarmed_confirmed and a.capture_tools_authorized):p.error('Explicit approved isolated/capture execution required')
 os.umask(0o077);assert os.path.ismount('/var/lib/private-services')
 assert a.observer_config.resolve().is_relative_to('/var/lib/private-services')
 observer=json.loads(a.observer_config.read_text())
 r=Path('/var/lib/private-services/agent-state/jeremy/garden-device-backups');d=Path((r/'current-sunroom2-usb').read_text().strip());release=d/'single-ap-trial-release';baseline=d/'wifi-ps-off-release';target=json.loads((release/'target.local.json').read_text());manifest=json.loads((release/'manifest.local.json').read_text())
 for name,h in manifest['sources'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert hashlib.sha256((release/'garden_native_probe.bin').read_bytes()).hexdigest()==manifest['image']['image_sha256']
 bm=json.loads((baseline/'manifest.local.json').read_text());assert hashlib.sha256((baseline/'garden_native_probe.bin').read_bytes()).hexdigest()==bm['image']['image_sha256']
 journal=d/(a.run_id+'-controlled.execution.local.json');assert not journal.exists(),'Existing execution: inspect, NEVER replay'
 state={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'starting','trial_upload_attempts':0,'baseline_upload_attempts':0}
 def save():
  tmp=journal.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(journal)
 with journal.open('x') as f:json.dump(state,f)
 aliases=json.loads((d/'wifi-ps-off-first-capture.local.json').read_text())['ap_aliases'];ap=next(k for k,v in aliases.items() if v=='OpenWrt primary phy1-ap0');fmt=lambda s:':'.join(s[i:i+2] for i in range(0,12,2));nonce=uuid.uuid4().hex;tools=json.loads((d/'wifi-capture-tools-staging.local.json').read_text());assert tools['exit']==0
 plan={'monitor':'gc'+nonce[:10],'owner_tag':nonce,'tool_directory':tools['temporary_public_tool_directory'],'station_mac':fmt(target['expected_device_id']),'ap_mac':fmt(ap),'base_interface':'phy1-ap0',**{k:observer[k] for k in ('observer_host','workstation','key','known_hosts')}}
 pp=d/(a.run_id+'-observer-plan.local.json');pp.write_text(json.dumps(plan,indent=2)+'\n');pcap=d/(a.run_id+'-observer.pcap');log=d/(a.run_id+'-observer.stderr.log');obsfile=ROOT.parents[2]/'home-network/scripts/garden-wifi-observer.py';spec=importlib.util.spec_from_file_location('obs',obsfile);obs=importlib.util.module_from_spec(spec);spec.loader.exec_module(obs);state['observer_source_sha256']=hashlib.sha256(obsfile.read_bytes()).hexdigest();save();child=None
 def remote(command):
  inner=['ssh','-i',plan['key'],'-o','BatchMode=yes','-o','ConnectTimeout=4','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+plan['known_hosts'],'root@'+plan['observer_host'],command]
  return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',plan['workstation'],shlex.join(inner)],capture_output=True,timeout=15)
 def upload(label,rel):
  jp=d/(label+'-ota.execution.local.json');assert not jp.exists()
  state['state']=label+'_upload_starting';save()
  with (d/(label+'-ota.stdout.local.json')).open('xb') as out,(d/(label+'-ota.stderr.log')).open('xb') as err:
   cp=subprocess.run([sys.executable,str(ROOT/'scripts/controller_ota.py'),'--target',str(rel/'target.local.json'),'--image',str(rel/'garden_native_probe.bin'),'--journal',str(jp),'--apply','--maintenance-confirmed','--equipment-power-off-confirmed','--remote-reboot-confirmed','--verification-timeout','600'],stdout=out,stderr=err,timeout=780)
  j=json.loads(jp.read_text());state['trial_upload_attempts' if rel==release else 'baseline_upload_attempts']=j.get('upload_attempts',0);state[label+'_ota_state']=j['state'];save();assert cp.returncode==0 and j['state']=='confirmed','Inspect actual state; no upload replay'
  print(label,'OTA confirmed; uploads:',j['upload_attempts'],flush=True);return j
 try:
  child=obs.run(plan,pcap,log);observer_started=time.monotonic();state['observer_ssh_pid']=child.pid;state['state']='observer_starting';save()
  deadline=time.monotonic()+15
  while time.monotonic()<deadline:
   if child.poll() is not None:raise RuntimeError('Observer exited before trial; inspect capture log')
   if pcap.stat().st_size>=24 and 'OBSERVER_READY' in log.read_text():break
   time.sleep(.2)
  else:raise RuntimeError('Observer not ready; no trial upload issued')
  with pcap.open('rb') as f:header=f.read(24)
  endian='<' if header[:4]==b'\xd4\xc3\xb2\xa1' else '>'
  assert struct.unpack(endian+'I',header[20:24])[0]==127,'Require radiotap over-air capture'
  state['state']='observer_ready';save();print('Independent radiotap observer ready; starting ONE trial upload.',flush=True)
  trial=upload(a.run_id+'-trial',release);after=trial['after'];assert after['wifi'].get('single_ap_trial_enabled') is True and after['wifi'].get('single_ap_trial_pending') is False and after['wifi']['power_save_mode']==0
  t=Transport(target['host']);trace=t.get('/api/wifi/diagnostics');(d/(a.run_id+'-trial-trace.local.json')).write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'trace':trace,'wifi':t.get('/api/wifi/status')},indent=2)+'\n');state['state']='trial_complete_original_auto_restored';save()
  print('20-second trial finished; original auto config restored, GPIO unarmed. Restoring baseline image.',flush=True)
  restored=upload(a.run_id+'-baseline-restore',baseline);assert restored['after']['ota']['elf_sha256']==bm['image']['elf_sha256'];assert restored['after']['wifi']['power_save_mode']==0 and not restored['after']['io']['gpio_active'];state['state']='baseline_restored';save()
  try:child.wait(timeout=185)
  except subprocess.TimeoutExpired:child.kill();child.wait();state['observer_timeout']=True;save()
  state['observer_exit']=child.returncode;state['pcap_bytes']=pcap.stat().st_size;save()
 finally:
  if child and child.poll() is None:child.terminate()
  if child:
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:child.kill();child.wait()
  # Let the bounded independent fuse retire before declaring the task complete.
  if child and time.monotonic()-observer_started<174:time.sleep(174-(time.monotonic()-observer_started))
  # Independent 170s fuse also protects cleanup after management-link loss.
  name=plan['monitor'];tag=plan['owner_tag'];folder=plan['tool_directory']
  cmd=f'''if [ -e /sys/class/net/{name} ]; then own=$(awk '{{print}}' /sys/class/net/{name}/ifalias); if [ "$own" = {tag} ] || [ -z "$own" ]; then iw dev {name} del; fi; fi; rm -rf {folder}; printf '@@MONITOR_ABSENT@@\\n'; test ! -e /sys/class/net/{name} && echo yes; printf '@@TOOLS_ABSENT@@\\n'; test ! -e {folder} && echo yes; printf '@@RADIO@@\\n'; iw dev phy1-ap0 info; printf '@@HASHES@@\\n'; sha256sum /etc/config/network /etc/config/wireless; printf '@@AP@@\\n'; ubus call hostapd.phy1-ap0 get_status; printf '@@MEM@@\\n'; grep MemAvailable /proc/meminfo'''
  try:
   cp=remote(cmd);(d/(a.run_id+'-observer-cleanup.stdout.log')).write_bytes(cp.stdout);(d/(a.run_id+'-observer-cleanup.stderr.log')).write_bytes(cp.stderr);state['cleanup_exit']=cp.returncode;state['monitor_absent']='@@MONITOR_ABSENT@@\nyes' in cp.stdout.decode();state['tools_absent']='@@TOOLS_ABSENT@@\nyes' in cp.stdout.decode();save()
  except Exception as e:state['cleanup_uncertain']=type(e).__name__;save()
 if state.get('state')=='baseline_restored' and state.get('monitor_absent') and state.get('tools_absent'):
  state['state']='completed';state['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print('Baseline restored; monitor/tools absent. Raw capture stays in vault.',flush=True)
 else:raise RuntimeError('Execution incomplete; inspect state/journals, no replay')
if __name__=='__main__':main()
