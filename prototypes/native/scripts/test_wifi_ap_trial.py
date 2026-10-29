#!/usr/bin/env python3
"""Actual bounded trial C module, fake SDK; no device/network access."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
header='''#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_INVALID_STATE 1
#define ESP_ERR_INVALID_ARG 2
#define WIFI_IF_STA 0
typedef struct {struct {uint8_t ssid[32],password[64],bssid[6];bool bssid_set;int channel;}sta;} wifi_config_t;
esp_err_t esp_wifi_stop(void);
esp_err_t esp_wifi_set_config(int,wifi_config_t*);
esp_err_t esp_wifi_start(void);
'''
harness='''#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include "wifi_ap_trial.h"
static int calls,fail;static wifi_config_t restored;
esp_err_t esp_wifi_stop(void){assert(calls++==0);return fail==1?99:0;}
esp_err_t esp_wifi_set_config(int i,wifi_config_t*c){assert(i==0&&calls++==1);restored=*c;return fail==2?99:0;}
esp_err_t esp_wifi_start(void){assert(calls++==2);return fail==3?99:0;}
int main(int argc,char**argv){
 fail=argc>1?atoi(argv[1]):0;wifi_config_t cfg={0},orig={0};cfg.sta.channel=orig.sta.channel=11;
 uint32_t now=0xfffff000u;
#ifdef CONFIG_GARDEN_WIFI_SINGLE_AP_TRIAL
 assert(wifi_ap_trial_enabled()&&wifi_ap_trial_pending());
 int err=wifi_ap_trial_prepare(&cfg,now);
#ifdef BAD_BSSID
 assert(err==ESP_ERR_INVALID_ARG);assert(!memcmp(&cfg,&orig,sizeof(cfg)));return 0;
#endif
 assert(err==0&&cfg.sta.bssid_set&&cfg.sta.bssid[0]==2);
 assert(wifi_ap_trial_prepare(&cfg,now)==ESP_ERR_INVALID_STATE);
 assert(wifi_ap_trial_poll(now+19999)==0&&calls==0&&wifi_ap_trial_pending());
 err=wifi_ap_trial_poll(now+20000);
 if(fail){assert(err==99&&wifi_ap_trial_pending()&&calls==fail);return 0;}
 assert(err==0&&calls==3&&!wifi_ap_trial_pending());assert(!memcmp(&orig,&restored,sizeof(orig)));
 assert(wifi_ap_trial_poll(now+21000)==0&&calls==3);
#else
 assert(!wifi_ap_trial_enabled()&&!wifi_ap_trial_pending());
 assert(wifi_ap_trial_prepare(&cfg,now)==0&&!memcmp(&cfg,&orig,sizeof(cfg)));
 assert(wifi_ap_trial_poll(now+20000)==0&&calls==0);
#endif
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'esp_wifi.h').write_text(header);(p/'sdkconfig.h').write_text('');(p/'test.c').write_text(harness)
 for bssid in [None,'02:11:22:33:44:55','00:00:00:00:00:00','01:11:22:33:44:55','bad']:
  flags=[] if bssid is None else ['-DCONFIG_GARDEN_WIFI_SINGLE_AP_TRIAL=1',f'-DCONFIG_GARDEN_WIFI_TRIAL_BSSID="{bssid}"']
  if bssid not in [None,'02:11:22:33:44:55']:flags+=['-DBAD_BSSID=1']
  subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',*flags,'-I'+str(p),'-I'+str(root/'main'),str(p/'test.c'),str(root/'main/wifi_ap_trial.c'),'-o',str(p/'test')],check=True)
  for fail in ([0,1,2,3] if bssid=='02:11:22:33:44:55' else [0]):subprocess.run([str(p/'test'),str(fail)],check=True)
s=(root/'main/runtime.c').read_text()
assert 'if (!wifi_ap_trial_pending()) ota_heartbeat(1);' in s
assert 'Temporary trial firmware cannot arm' in s
assert 'ESP_ERROR_CHECK(wifi_ap_trial_poll(' in s
for f in root.glob('sdkconfig*.defaults'):assert 'CONFIG_GARDEN_WIFI_SINGLE_AP_TRIAL=y' not in f.read_text()
print('WIFI_AP_TRIAL_HOST_TEST PASS: default off, 20s/wrap, exact original restore, each SDK failure holds pending, bad MACs, heartbeat/arm/default guards')
