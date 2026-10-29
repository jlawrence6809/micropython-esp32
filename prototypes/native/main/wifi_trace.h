#pragma once
#include <stdint.h>
#include <stdbool.h>

#define WIFI_TRACE_CAPACITY 32

typedef enum {
    WIFI_TRACE_START, WIFI_TRACE_ATTEMPT, WIFI_TRACE_LINK_UP,
    WIFI_TRACE_GOT_IP, WIFI_TRACE_DISCONNECT, WIFI_TRACE_CONNECT_ERROR
} wifi_trace_kind;
typedef struct {
    uint64_t sequence, monotonic_ms;
    wifi_trace_kind kind;
    int32_t reason, error;
    int16_t channel, rssi, authmode; /* -1 channel/authmode and 0 RSSI mean unknown */
    uint8_t bssid[6]; /* zero means unknown; never store SSID/password */
} wifi_trace_event;
typedef struct {
    uint64_t written;
    wifi_trace_event events[WIFI_TRACE_CAPACITY];
} wifi_trace;

/* Caller synchronizes append/snapshot. No SDK, flash, allocation or I/O. */
void wifi_trace_append(wifi_trace *,wifi_trace_event);
unsigned wifi_trace_count(const wifi_trace *);
const wifi_trace_event *wifi_trace_at(const wifi_trace *,unsigned chronological_index);
const char *wifi_trace_name(wifi_trace_kind);
bool wifi_trace_bssid_known(const uint8_t bssid[6]);
