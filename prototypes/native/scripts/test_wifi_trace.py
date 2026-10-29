#!/usr/bin/env python3
"""Host-only tests of the actual bounded Wi-Fi trace; no SDK/network/device."""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parent.parent
code=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "wifi_trace.h"
int main(void) {
 wifi_trace ring={0};assert(wifi_trace_count(&ring)==0&&!wifi_trace_at(&ring,0));
 uint8_t mac[6]={1,2,3,4,5,6},zero[6]={0};
 assert(wifi_trace_bssid_known(mac)&&!wifi_trace_bssid_known(zero));
 wifi_trace_event e={.monotonic_ms=4294967296ULL,.kind=WIFI_TRACE_DISCONNECT,.reason=7,.error=-5,.channel=-1,.rssi=-61,.authmode=-1};
 memcpy(e.bssid,mac,6);wifi_trace_append(&ring,e);memset(e.bssid,0,6);
 const wifi_trace_event *first=wifi_trace_at(&ring,0);
 assert(first->sequence==1&&first->monotonic_ms==4294967296ULL&&first->reason==7&&first->error==-5&&first->rssi==-61&&first->authmode==-1&&!memcmp(first->bssid,mac,6));
 assert(!wifi_trace_at(&ring,1));
 for(unsigned i=1;i<100;i++){e.monotonic_ms=4294967296ULL+i;wifi_trace_append(&ring,e);}
 assert(wifi_trace_count(&ring)==WIFI_TRACE_CAPACITY&&ring.written==100);
 for(unsigned i=0;i<WIFI_TRACE_CAPACITY;i++){
  const wifi_trace_event *row=wifi_trace_at(&ring,i);assert(row->sequence==69+i&&row->monotonic_ms==4294967296ULL+68+i);
 }
 assert(!wifi_trace_at(&ring,WIFI_TRACE_CAPACITY));
 wifi_trace snapshot=ring;wifi_trace_append(&ring,e);assert(snapshot.written==100&&wifi_trace_at(&snapshot,0)->sequence==69);
 ring=(wifi_trace){.written=4294967290ULL};
 for(unsigned i=0;i<100;i++)wifi_trace_append(&ring,e);
 assert(ring.written==4294967390ULL&&wifi_trace_at(&ring,31)->sequence==4294967390ULL);
 for(int i=WIFI_TRACE_START;i<=WIFI_TRACE_CONNECT_ERROR;i++)assert(strcmp(wifi_trace_name(i),"unknown"));
 assert(!strcmp(wifi_trace_name(99),"unknown"));
 puts("WIFI_TRACE_HOST_TEST PASS: empty, deep copy, bound/wrap/order, snapshot, >32-bit time/sequence, event names");return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='garden-wifi-trace-') as tmp:
    t=Path(tmp);(t/'test.c').write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(root/'main'),str(root/'main/wifi_trace.c'),str(t/'test.c'),'-o',str(t/'test')],check=True)
    subprocess.run([str(t/'test')],check=True)
