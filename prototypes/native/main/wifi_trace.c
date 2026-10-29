#include <stddef.h>
#include "wifi_trace.h"

void wifi_trace_append(wifi_trace *trace,wifi_trace_event event)
{
    event.sequence=trace->written+1;
    trace->events[trace->written%WIFI_TRACE_CAPACITY]=event;
    trace->written++;
}
unsigned wifi_trace_count(const wifi_trace *trace)
{
    return trace->written<WIFI_TRACE_CAPACITY?(unsigned)trace->written:WIFI_TRACE_CAPACITY;
}
const wifi_trace_event *wifi_trace_at(const wifi_trace *trace,unsigned index)
{
    unsigned count=wifi_trace_count(trace);
    if (index>=count) return NULL;
    uint64_t oldest=trace->written-count;
    return &trace->events[(oldest+index)%WIFI_TRACE_CAPACITY];
}
const char *wifi_trace_name(wifi_trace_kind kind)
{
    switch (kind) {
        case WIFI_TRACE_START:return "station_start";
        case WIFI_TRACE_ATTEMPT:return "connect_attempt";
        case WIFI_TRACE_LINK_UP:return "associated";
        case WIFI_TRACE_GOT_IP:return "got_ip";
        case WIFI_TRACE_DISCONNECT:return "disconnected";
        case WIFI_TRACE_CONNECT_ERROR:return "connect_call_error";
    }
    return "unknown";
}
bool wifi_trace_bssid_known(const uint8_t bssid[6])
{
    for (unsigned i=0;i<6;i++) if (bssid[i]) return true;
    return false;
}
