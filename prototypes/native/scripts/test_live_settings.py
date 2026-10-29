#!/usr/bin/env python3
"""Host C tests of real backend/profile/commit code; SDK I/O and NVS are fakes.
No device access. Requires a C compiler, libcrypto.so.3 and IDF's cJSON source.
"""
from pathlib import Path
import json
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent
JSON=Path.home()/'.local/share/esp/esp-idf-v5.5.1/components/json/cJSON'
def function(source,name):
    start=source.index(name);start=source.rfind('\n',0,start)+1
    begin=source.index('{',start);depth=0
    for end in range(begin,len(source)):
        depth+=(source[end]=='{')-(source[end]=='}')
        if depth==0:return source[start:end+1]+'\n'
    raise ValueError('Unbalanced function')
with tempfile.TemporaryDirectory(prefix='garden-live-settings-') as tmp:
    t=Path(tmp);(t/'driver').mkdir();(t/'mbedtls').mkdir()
    (t/'esp_err.h').write_text('#pragma once\ntypedef int esp_err_t;\n#define ESP_OK 0\n#define ESP_FAIL -1\n#define ESP_ERR_INVALID_ARG 2\n#define ESP_ERR_INVALID_STATE 3\nconst char *esp_err_to_name(int);\n')
    (t/'driver/i2c_master.h').write_text('#pragma once\ntypedef void *i2c_master_bus_handle_t;typedef void *i2c_master_dev_handle_t;\n')
    # Host-only streaming shim buffers input and hashes it with real OpenSSL.
    # This exercises revision hashing, NOT MCU stack/heap requirements.
    (t/'mbedtls/sha256.h').write_text(r'''#pragma once
#include <stddef.h>
#include <string.h>
extern unsigned char *SHA256(const unsigned char *,size_t,unsigned char *);
static inline int mbedtls_sha256(const unsigned char *p,size_t n,unsigned char *o,int unused){(void)unused;return SHA256(p,n,o)?0:1;}
typedef struct {unsigned char data[65536];size_t used;} mbedtls_sha256_context;
static inline void mbedtls_sha256_init(mbedtls_sha256_context *c){c->used=0;}
static inline void mbedtls_sha256_free(mbedtls_sha256_context *c){(void)c;}
static inline int mbedtls_sha256_starts(mbedtls_sha256_context *c,int is224){c->used=0;return is224?-1:0;}
static inline int mbedtls_sha256_update(mbedtls_sha256_context *c,const unsigned char *p,size_t n){if(n>sizeof(c->data)-c->used)return -1;memcpy(c->data+c->used,p,n);c->used+=n;return 0;}
static inline int mbedtls_sha256_finish(mbedtls_sha256_context *c,unsigned char *out){return SHA256(c->data,c->used,out)?0:-1;}
''')
    board=(ROOT/'main/board_io.c').read_text();runtime=(ROOT/'main/runtime.c').read_text()
    code=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <setjmp.h>
#include "io_backend.h"
#include "target_board.h"
#include "device_profile.h"
static int gpio_error,gpio_level;
static int gpio_set_level(int pin,int level) {(void)pin;if(gpio_error)return ESP_FAIL;gpio_level=level;return ESP_OK;}
const char *esp_err_to_name(int e){(void)e;return "fake";}
int evaluate_inputs(const char *s,const rule_inputs *i,char *e,size_t n,size_t *p){(void)s;(void)i;(void)e;(void)n;(void)p;return -1;}
rule_inputs rule_inputs_default(void){return (rule_inputs){.time_seconds=-1,.last_time_seconds=-1};}
bool clock_service_zone_supported(const char *s){return !strcmp(s,"UTC")||!strcmp(s,"America/Los_Angeles");}
bool clock_service_use_zone(const char *s){return !s||clock_service_zone_supported(s);}
'''
    for name in ('io_pin_allowed(', 'relay_gpio_level(', 'relay_gpio_configure(', 'switch_debounce_init(', 'switch_debounce_update(', 'board_io_plan('):code+=function(board,name)
    code+=r'''
static bool outputs_applied=true,persistence_uncertain,uploading;
static int commit_status,edit_generation,store,nvs_fail,nvs_calls;
static io_backend outputs;
static engine_mock mock_outputs;
static cJSON *device_profile,*relays;
static char armed_layout[65],device_id[13]="123456abcdef";
static char saved_profile[10000],saved_arm[80];
#define MAX_BODY 12288
static const char *text(cJSON *o,const char *k){cJSON *v=cJSON_GetObjectItemCaseSensitive(o,k);return cJSON_IsString(v)?v->valuestring:NULL;}
static bool ota_upload_in_progress(void){return uploading;}
static int64_t esp_timer_get_time(void){return 1000000;}
static int nvs_set_str(int h,const char *k,const char *v){(void)h;nvs_calls++;if(nvs_calls==nvs_fail)return ESP_FAIL;strcpy(!strcmp(k,"arm_v1")?saved_arm:saved_profile,v);return ESP_OK;}
static int nvs_commit(int h){(void)h;nvs_calls++;return nvs_calls==nvs_fail?ESP_FAIL:ESP_OK;}
static engine_time_guard runtime_clock;
static rule_inputs simulated_inputs;
static bool use_network_clock;
static char hostname[64]="garden-bench",active_hostname[64]="garden-bench";
static const char *fake_stored_profile;
static jmp_buf boot_failure;
static bool expected_boot_failure;
#define ESP_ERR_NVS_NOT_FOUND 10
#define ESP_ERR_INVALID_SIZE 11
#define ESP_ERR_INVALID_VERSION 12
#define ESP_ERR_INVALID_STATE 3
#define configASSERT assert
#define valid_relays profile_valid_relays
#define ESP_ERROR_CHECK(expr) do {int rc_=(expr);if(rc_!=ESP_OK){if(expected_boot_failure)longjmp(boot_failure,1);assert(rc_==ESP_OK);}}while(0)
static cJSON *clock_service_status(void){cJSON *o=cJSON_CreateObject();cJSON_AddNullToObject(o,"timezone");return o;}
static cJSON *parse(const char *s){return cJSON_Parse(s);}
static int nvs_get_str(int h,const char *key,char *dest,size_t *size){
 (void)h;if(strcmp(key,"profile_v1")||!fake_stored_profile)return ESP_ERR_NVS_NOT_FOUND;
 size_t n=strlen(fake_stored_profile)+1;if(!dest){*size=n;return ESP_OK;}
 if(*size<n)return ESP_ERR_INVALID_SIZE;
 memcpy(dest,fake_stored_profile,n);*size=n;return ESP_OK;
}
'''
    for name in ('static void put_bool(', 'static void adopt_profile(', 'static void load_relays(', 'static void load_profile('):code+=function(runtime,name)
    code+=function(runtime,'static bool commit_profile(')
    code+='static const char relay_x8_template[]='+json.dumps((ROOT/'profiles/relay_x8_unarmed.json').read_text())+';\n'
    code+=r'''
static bool inv,command,write_error;
static int writes,swopens,swcloses,swfail_open=-1,swfail_close=-1;
static bool swraw[2],swopened[2];
static int ro(void*c,unsigned i,int p,bool n,bool v){(void)c;(void)i;(void)p;inv=n;command=v;return ESP_OK;}
static int rs(void*c,unsigned i,bool v){(void)c;(void)i;writes++;if(write_error)return ESP_FAIL;command=v;return ESP_OK;}
static int rc(void*c,unsigned i){(void)c;(void)i;return ESP_OK;}
static int so(void*c,unsigned i,int p,uint32_t n){(void)c;(void)n;swopens++;swopened[i]=true;return p==swfail_open?ESP_FAIL:ESP_OK;}
static int sc(void*c,unsigned i){(void)c;swcloses++;if(outputs.switch_pins[i]==swfail_close)return ESP_FAIL;swopened[i]=false;return ESP_OK;}
static bool ss(void*c,unsigned i,uint32_t n){(void)c;(void)n;return swraw[i];}
static int rr(void*c,unsigned i,bool n,bool v){int err=rs(c,i,v);if(!err)inv=n;return err;}
static const io_operations ops={ro,rs,rc,so,ss,sc,rr};
static void setup(void){
 if(device_profile)cJSON_Delete(device_profile);
 cJSON *a=cJSON_Parse("[{\"pin\":4,\"label\":\"Flood light\",\"rule\":\"return nil\",\"value\":false,\"auto\":false,\"isInverted\":true,\"defaultValue\":false,\"defaultAuto\":false}]");
 device_profile=profile_from_legacy(a,"UTC");cJSON_Delete(a);assert(device_profile);
 relays=cJSON_GetObjectItemCaseSensitive(device_profile,"relays");outputs=(io_backend){0};
 assert(io_backend_start(&outputs,device_profile,&ops,&outputs,0)==ESP_OK);
 assert(io_layout_hash(device_profile,armed_layout));mock_outputs=(engine_mock){0};
 nvs_fail=nvs_calls=writes=edit_generation=swopens=swcloses=0;swfail_open=swfail_close=-1;
 swraw[0]=swraw[1]=swopened[0]=swopened[1]=false;
 uploading=persistence_uncertain=write_error=false;outputs_applied=true;
}
static cJSON *changed(const char *key,bool value){cJSON *p=cJSON_Duplicate(device_profile,true);cJSON *r=cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(p,"relays"),0);cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(r,key),value);return p;}
static cJSON *input_change(int light,int reset){cJSON *p=cJSON_Duplicate(device_profile,true),*s=cJSON_GetObjectItemCaseSensitive(p,"sensor_pins");cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(s,"light_switch"),light);cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(s,"reset_switch"),reset);return p;}
int main(void){
 cJSON *raw=cJSON_Parse(relay_x8_template),*normalized=profile_normalize(raw);assert(raw);cJSON_Delete(raw);
 #if defined(CONFIG_IDF_TARGET_ESP32)
 assert(normalized);char template_hash[65];assert(io_layout_hash(normalized,template_hash));
 #else
 assert(!normalized); /* Original-ESP32 pins must not leak into S3 policy. */
 #endif
 cJSON_Delete(normalized);
 assert(io_backend_selftests());
 assert(profile_edit_selftests());
 /* Real empty-NVS startup path, not just a hand-constructed profile fixture. */
 load_relays();assert(relays);load_profile();assert(device_profile);
 cJSON *factory=cJSON_GetArrayItem(relays,0);assert(cJSON_GetArraySize(relays)==1);
 #if defined(CONFIG_IDF_TARGET_ESP32)
 assert(cJSON_GetObjectItemCaseSensitive(factory,"pin")->valueint==4);
 #else
 assert(cJSON_GetObjectItemCaseSensitive(factory,"pin")->valueint==1);
 #endif
 assert(!cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(factory,"value")));
 assert(!cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(factory,"auto")));
 assert(!cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(factory,"defaultValue")));
 assert(!cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(factory,"defaultAuto")));
 assert(!use_network_clock&&!outputs.active&&nvs_calls==0);
 assert(!strcmp(hostname,"garden-bench")&&!strcmp(hostname,active_hostname));
 cJSON_Delete(device_profile);device_profile=relays=NULL;
 /* Unknown/corrupt SAVED profiles must still fail closed, never default. */
 const char *bad_profiles[]={"{}","{\"format_version\":999}"};
 for(unsigned i=0;i<2;i++){
  fake_stored_profile=bad_profiles[i];load_relays();expected_boot_failure=true;
  if(!setjmp(boot_failure)){load_profile();assert(!"Corrupt stored profile accepted");}
  expected_boot_failure=false;assert(!device_profile);cJSON_Delete(relays);relays=NULL;
 }
 fake_stored_profile=NULL;
 puts("BLANK_NVS_BOOT_HOST_TEST PASS (real loaders/adoption; fake NVS/clock)");
 relay_gpio g={.pin=4,.opened=true,.inverted=true,.command=false};
 assert(relay_gpio_configure(&g,false,false)==ESP_OK&&!g.inverted&&!g.command&&gpio_level==0);
 gpio_error=1;assert(relay_gpio_configure(&g,true,true)!=ESP_OK&&!g.inverted&&!g.command);gpio_error=0;
 setup();char old[65];strcpy(old,armed_layout);cJSON *p=changed("defaultAuto",true);
 assert(commit_profile(p,false)&&outputs_applied&&outputs.active&&strcmp(old,armed_layout));
 char hash[65];assert(io_layout_hash(device_profile,hash)&&!strcmp(hash,armed_layout)&&io_arm_record_matches(saved_arm,device_id,hash));
 assert(inv&&!command); /* default AUTO never changes present logical command */
 p=changed("isInverted",false);assert(commit_profile(p,false)&&outputs_applied&&!inv&&!command);
 assert(io_layout_hash(device_profile,hash)&&!strcmp(hash,armed_layout)&&io_arm_record_matches(saved_arm,device_id,hash));
 setup();p=changed("isInverted",false);write_error=true;
 assert(commit_profile(p,false)&&!outputs_applied&&inv&&outputs.inverted[0]&&!outputs.commands[0]);
 for(int fail=1;fail<=3;fail++){
  setup();p=changed("defaultAuto",true);nvs_fail=fail;
  assert(!commit_profile(p,false)&&persistence_uncertain&&writes==0&&edit_generation==0);cJSON_Delete(p);
  nvs_fail=0;p=changed("defaultAuto",true);assert(!commit_profile(p,false)&&commit_status==503);cJSON_Delete(p);
 }
 setup();armed_layout[0]=0;p=changed("defaultAuto",true);
 assert(!commit_profile(p,false)&&commit_status==409&&nvs_calls==0&&writes==0);cJSON_Delete(p);
 setup();p=cJSON_Duplicate(device_profile,true);cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(p,"relays"),0),"pin"),5);
 assert(!commit_profile(p,false)&&commit_status==409&&nvs_calls==0&&writes==0);cJSON_Delete(p);
 setup();uploading=true;p=changed("defaultAuto",true);assert(!commit_profile(p,false)&&commit_status==503&&writes==0);cJSON_Delete(p);
 /* Live input-only transaction: no relay GPIO writes, baseline held contact. */
 setup();swraw[0]=true;simulated_inputs.time_seconds=123;simulated_inputs.last_time_seconds=122;simulated_inputs.temperature=25;
 p=input_change(18,-1);assert(io_live_switch_settings_compatible(device_profile,p));
 assert(commit_profile(p,false)&&outputs_applied&&outputs.active&&writes==0&&swopens==1&&swcloses==0);
 assert(outputs.switch_pins[0]==18&&swopened[0]&&simulated_inputs.switch_state&&simulated_inputs.last_switch_state);
 assert(simulated_inputs.time_seconds==123&&simulated_inputs.last_time_seconds==122&&simulated_inputs.temperature==25);
 assert(io_layout_hash(device_profile,hash)&&!strcmp(hash,armed_layout)&&io_arm_record_matches(saved_arm,device_id,hash));
 swraw[0]=false;p=input_change(17,-1);assert(commit_profile(p,false)&&writes==0&&outputs.switch_pins[0]==17&&swcloses==1);
 assert(!simulated_inputs.switch_state&&!simulated_inputs.last_switch_state);
 p=input_change(-1,-1);assert(commit_profile(p,false)&&writes==0&&outputs.switch_pins[0]==-1&&!swopened[0]);
 /* Two inputs can be swapped without taking a relay down. */
 p=input_change(18,17);assert(commit_profile(p,false));p=input_change(17,18);assert(commit_profile(p,false)&&writes==0);
 assert(outputs.switch_pins[0]==17&&outputs.switch_pins[1]==18);
 /* Every current/default/AUTO must be OFF in old AND candidate profile. */
 const char *off_fields[]={"value","auto","defaultValue","defaultAuto"};
 for(unsigned i=0;i<4;i++){
  setup();cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(relays,0),off_fields[i]),true);p=input_change(18,-1);
  assert(!commit_profile(p,false)&&commit_status==409&&nvs_calls==0&&swopens==0);cJSON_Delete(p);
  setup();p=input_change(18,-1);cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(p,"relays"),0),off_fields[i]),true);
  assert(!commit_profile(p,false)&&commit_status==409&&nvs_calls==0&&swopens==0);cJSON_Delete(p);
 }
 setup();p=input_change(18,-1);cJSON_SetBoolValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(cJSON_GetObjectItemCaseSensitive(p,"relays"),0),"isInverted"),false);
 assert(!commit_profile(p,false)&&swopens==0);cJSON_Delete(p);
 setup();p=input_change(4,-1);assert(!commit_profile(p,false)&&swopens==0);cJSON_Delete(p);
 setup();p=input_change(18,-1);cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetObjectItemCaseSensitive(p,"sensor_pins"),"photo_sensor"),17);
 assert(!commit_profile(p,false)&&swopens==0);cJSON_Delete(p);
 #if defined(CONFIG_IDF_TARGET_ESP32)
 setup();p=input_change(5,-1);assert(!commit_profile(p,false)&&swopens==0);cJSON_Delete(p);
 #endif
 setup();armed_layout[0]=0;p=input_change(18,-1);assert(!commit_profile(p,false)&&commit_status==409&&swopens==0);cJSON_Delete(p);
 /* Partial input-open failure cleaned up; no profile/arm written. */
 setup();swfail_open=18;p=input_change(18,-1);assert(!commit_profile(p,false)&&nvs_calls==0&&writes==0&&!persistence_uncertain&&outputs_applied&&!outputs.cleanup_failed&&!swopened[0]&&outputs.switch_pins[0]==-1);cJSON_Delete(p);
 /* Failed remap restores existing input and establishes fresh baseline. */
 setup();p=input_change(18,-1);assert(commit_profile(p,false));nvs_calls=writes=0;swraw[0]=true;swfail_open=17;p=input_change(17,-1);
 assert(!commit_profile(p,false)&&nvs_calls==0&&writes==0&&outputs.switch_pins[0]==18&&swopened[0]&&!outputs.cleanup_failed&&simulated_inputs.switch_state&&simulated_inputs.last_switch_state);cJSON_Delete(p);
 for(int fail=1;fail<=3;fail++){
  setup();nvs_fail=fail;p=input_change(18,-1);assert(!commit_profile(p,false)&&persistence_uncertain&&writes==0&&edit_generation==0&&outputs.switch_pins[0]==-1&&!swopened[0]&&swopens==1&&swcloses==1);cJSON_Delete(p);
 }
 /* Cleanup/rollback failures must not advertise successful applied settings. */
 setup();p=input_change(18,-1);assert(commit_profile(p,false));swfail_close=18;nvs_calls=writes=0;p=input_change(-1,-1);
 assert(!commit_profile(p,false)&&persistence_uncertain&&!outputs_applied&&outputs.cleanup_failed&&nvs_calls==0&&writes==0);cJSON_Delete(p);
 setup();p=input_change(18,-1);assert(commit_profile(p,false));swfail_open=18;nvs_calls=0;nvs_fail=1;p=input_change(17,-1);
 assert(!commit_profile(p,false)&&persistence_uncertain&&!outputs_applied&&writes==0);cJSON_Delete(p);
 puts("LIVE_SWITCH_INPUT_HOST_TEST PASS (enable/remap/remove/swap, all-OFF gate, baseline, NVS/GPIO rollback, no relay writes)");
 cJSON_Delete(device_profile);puts("LIVE_SETTINGS_HOST_TEST PASS (real backend, normalization, commit; fake GPIO/NVS)");return 0;
}
'''
    (t/'test.c').write_text(code)
    for target in ('ESP32S3','ESP32'):
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DCONFIG_IDF_TARGET_'+target+'=1','-I'+str(t),'-I'+str(ROOT/'main'),'-I'+str(JSON),str(t/'test.c'),str(ROOT/'main/io_backend.c'),str(ROOT/'main/device_profile.c'),str(ROOT/'main/profile_edit.c'),str(ROOT/'main/relay_engine.c'),str(JSON/'cJSON.c'),'-l:libcrypto.so.3','-lm','-o',str(t/'test')],check=True)
        subprocess.run([str(t/'test')],check=True)
        print('Target:',target)
