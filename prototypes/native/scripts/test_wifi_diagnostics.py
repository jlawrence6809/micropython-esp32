#!/usr/bin/env python3
"""Compile real diagnostic JSON code on host with fake timer/critical section.
Verifies bounds, field values, no secrets and no allocation/SDK calls under lock.
No network, USB or device operations.
"""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parent.parent
sdk_json=Path.home()/'.local/share/esp/esp-idf-v5.5.1/components/json/cJSON'
source=(root/'main/runtime.c').read_text()
def function(name):
    start=source.index(name);start=source.rfind('\n',0,start)+1;begin=source.index('{',start);depth=0
    for end in range(begin,len(source)):
        depth+=(source[end]=='{')-(source[end]=='}')
        if depth==0:return source[start:end+1]+'\n'
    raise ValueError('Unbalanced function')
code=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"
#include "wifi_trace.h"
static int depth,wifi_history_lock;
static wifi_trace wifi_history;
static void enter(int *lock){(void)lock;assert(!depth);depth++;}
static void leave(int *lock){(void)lock;assert(depth==1);depth--;}
#define portENTER_CRITICAL(x) enter(x)
#define portEXIT_CRITICAL(x) leave(x)
static void *alloc(size_t n){assert(!depth);return malloc(n);}
static void release(void *p){assert(!depth);free(p);}
static long long esp_timer_get_time(void){assert(!depth);return 123456000LL;}
static const char *text(cJSON *o,const char *k){cJSON *v=cJSON_GetObjectItemCaseSensitive(o,k);return cJSON_IsString(v)?v->valuestring:NULL;}
static cJSON *ota_status(void){assert(!depth);return cJSON_Parse("{\"boot_id\":\"1234567890abcdef\"}");}
'''
code+=function('static void wifi_json_bssid(')+function('static cJSON *wifi_diagnostics(')
code+=r'''
int main(void){
 cJSON_Hooks hooks={alloc,release};cJSON_InitHooks(&hooks);
 cJSON *result=wifi_diagnostics();assert(result);
 assert(cJSON_GetArraySize(cJSON_GetObjectItemCaseSensitive(result,"events"))==0);
 assert(cJSON_GetObjectItemCaseSensitive(result,"uptime_ms")->valuedouble==123456);
 assert(!strcmp(text(result,"boot_id"),"1234567890abcdef"));cJSON_Delete(result);
 wifi_trace_event e={.kind=WIFI_TRACE_DISCONNECT,.channel=-1,.rssi=-61,.authmode=-1,.reason=7,.error=0,.bssid={1,2,3,4,5,6}};
 for(unsigned i=0;i<100;i++){e.monotonic_ms=i;wifi_trace_append(&wifi_history,e);}
 result=wifi_diagnostics();assert(result);cJSON *rows=cJSON_GetObjectItemCaseSensitive(result,"events");
 assert(cJSON_GetArraySize(rows)==32);
 assert(cJSON_GetObjectItemCaseSensitive(result,"total_events")->valuedouble==100);
 assert(cJSON_GetObjectItemCaseSensitive(result,"overwritten_events")->valuedouble==68);
 cJSON *row=cJSON_GetArrayItem(rows,0);
 assert(cJSON_GetObjectItemCaseSensitive(row,"sequence")->valuedouble==69);
 assert(cJSON_GetObjectItemCaseSensitive(row,"reason")->valueint==7);
 assert(cJSON_GetObjectItemCaseSensitive(row,"rssi")->valueint==-61);
 assert(cJSON_IsNull(cJSON_GetObjectItemCaseSensitive(row,"channel")));
 assert(cJSON_IsNull(cJSON_GetObjectItemCaseSensitive(row,"authmode")));
 assert(!strcmp(text(row,"event"),"disconnected")&&!strcmp(text(row,"bssid"),"01:02:03:04:05:06"));
 char *wire=cJSON_PrintUnformatted(result);assert(wire&&strlen(wire)<12000&&!strstr(wire,"\"ssid\"")&&!strstr(wire,"password"));
 free(wire);cJSON_Delete(result);
 cJSON *o=cJSON_CreateObject();uint8_t zero[6]={0};wifi_json_bssid(o,"bssid",zero);
 assert(cJSON_IsNull(cJSON_GetObjectItemCaseSensitive(o,"bssid")));cJSON_Delete(o);
 assert(!depth);puts("WIFI_DIAGNOSTICS_HOST_TEST PASS: actual JSON, 32-event bound, nulls, identity/time, no secrets/critical allocation");return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='garden-wifi-json-') as tmp:
    t=Path(tmp);(t/'test.c').write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(root/'main'),'-I'+str(sdk_json),str(t/'test.c'),str(root/'main/wifi_trace.c'),str(sdk_json/'cJSON.c'),'-o',str(t/'test')],check=True)
    subprocess.run([str(t/'test')],check=True)
