/* UTC sync plus explicit local timezone; profile persistence belongs to runtime. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdatomic.h>
#include "clock_service.h"
#include "esp_netif_sntp.h"
#include "esp_timer.h"
#include "nvs.h"

static const struct {const char *name,*posix;} zones[]={
    {"UTC","UTC0"},
    {"America/Los_Angeles","PST8PDT,M3.2.0/2,M11.1.0/2"},
    {"America/New_York","EST5EDT,M3.2.0/2,M11.1.0/2"},
};
static char selected[32]; /* empty = unconfirmed, even when UTC time is synced */
static nvs_handle_t store;
static atomic_bool synced;
static atomic_uint sync_count, last_sync_second, generation;

static const char *lookup(const char *name)
{
    if (!name || !*name) return NULL;
    for (unsigned i=0;i<sizeof(zones)/sizeof(zones[0]);i++)
        if (!strcmp(name,zones[i].name)) return zones[i].posix;
    return NULL;
}
static void on_sync(struct timeval *tv)
{
    if (tv->tv_sec<1577836800) return; /* reject pre-2020 clock as invalid */
    atomic_store(&synced,true);
    atomic_fetch_add(&sync_count,1);
    atomic_fetch_add(&generation,1);
    atomic_store(&last_sync_second,(unsigned)(esp_timer_get_time()/1000000));
}
bool clock_service_zone_supported(const char *name) {return name && lookup(name)!=NULL;}
bool clock_service_use_zone(const char *name)
{
    const char *posix=lookup(name);
    if (name && *name && !posix) return false;
    const char *saved=name?name:"";
    /* Calls are serialized by runtime's state mutex. SNTP only adjusts UTC and
       atomics; no application task reads localtime outside that mutex. */
    if (setenv("TZ",posix?posix:"UTC0",1)!=0) return false;
    tzset();snprintf(selected,sizeof(selected),"%s",saved);
    atomic_fetch_add(&generation,1);return true;
}
void clock_service_init(void)
{
    ESP_ERROR_CHECK(nvs_open("clock",NVS_READWRITE,&store));
    size_t size=sizeof(selected);
    esp_err_t err=nvs_get_str(store,"zone",selected,&size);
    if (err!=ESP_OK && err!=ESP_ERR_NVS_NOT_FOUND) ESP_ERROR_CHECK(err);
    if (err==ESP_ERR_NVS_NOT_FOUND) selected[0]=0;
    const char *posix=lookup(selected);
    /* Unknown persisted zones are not silently substituted for production use. */
    if (selected[0] && !posix) ESP_ERROR_CHECK(ESP_ERR_INVALID_STATE);
    if (setenv("TZ",posix?posix:"UTC0",1)!=0) ESP_ERROR_CHECK(ESP_ERR_NO_MEM);
    tzset();
    esp_sntp_config_t config=ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");
    config.start=false;config.wait_for_sync=false;config.sync_cb=on_sync;
    ESP_ERROR_CHECK(esp_netif_sntp_init(&config));
}
void clock_service_network_ready(void)
{
    /* Called after DHCP obtains an address; restarting also supports reconnects. */
    esp_err_t err=esp_netif_sntp_start();
    if (err!=ESP_OK) printf("CLOCK_SNTP_START_ERROR %s\n",esp_err_to_name(err));
}
cJSON *clock_service_zones(void)
{
    cJSON *o=cJSON_CreateArray();
    for (unsigned i=0;i<sizeof(zones)/sizeof(zones[0]);i++)
        cJSON_AddItemToArray(o,cJSON_CreateString(zones[i].name));
    return o;
}
bool clock_service_sample(int64_t *unix_seconds,int *local_seconds)
{
    time_t now=time(NULL);
    if (!selected[0] || !atomic_load(&synced) || now<1577836800) return false;
    struct tm local;
    if (!localtime_r(&now,&local)) return false;
    *unix_seconds=(int64_t)now;
    *local_seconds=local.tm_hour*3600+local.tm_min*60+local.tm_sec;
    return true;
}
cJSON *clock_service_view_at(long long unix_seconds)
{
    if (!selected[0]) return NULL;
    time_t at=(time_t)unix_seconds;struct tm local;
    if (!localtime_r(&at,&local)) return NULL;
    cJSON *o=cJSON_CreateObject();
    char formatted[32];strftime(formatted,sizeof(formatted),"%Y-%m-%dT%H:%M:%S",&local);
    cJSON_AddStringToObject(o,"local",formatted);
    cJSON_AddStringToObject(o,"timezone",selected);
    cJSON_AddBoolToObject(o,"is_dst",local.tm_isdst>0);
    cJSON_AddNumberToObject(o,"local_seconds",local.tm_hour*3600+local.tm_min*60+local.tm_sec);
    return o;
}
cJSON *clock_service_status(void)
{
    cJSON *o=cJSON_CreateObject();
    time_t now=time(NULL);
    bool valid=atomic_load(&synced) && now>=1577836800;
    cJSON_AddBoolToObject(o,"synchronized",valid);
    cJSON_AddBoolToObject(o,"timezone_confirmed",selected[0]!=0);
    cJSON_AddBoolToObject(o,"schedule_clock_valid",valid && selected[0]);
    cJSON_AddBoolToObject(o,"feeds_simulated_rules",false);
    if (selected[0]) cJSON_AddStringToObject(o,"timezone",selected);
    else cJSON_AddNullToObject(o,"timezone");
    cJSON_AddNumberToObject(o,"sync_count",atomic_load(&sync_count));
    cJSON_AddNumberToObject(o,"clock_generation",atomic_load(&generation));
    if (valid) {
        cJSON_AddNumberToObject(o,"unix_seconds",(double)now);
        cJSON_AddNumberToObject(o,"last_sync_age_seconds",(unsigned)(esp_timer_get_time()/1000000)-atomic_load(&last_sync_second));
        struct tm utc,local;
        gmtime_r(&now,&utc);localtime_r(&now,&local);
        char formatted[32];strftime(formatted,sizeof(formatted),"%Y-%m-%dT%H:%M:%SZ",&utc);
        cJSON_AddStringToObject(o,"utc",formatted);
        if (selected[0]) {
            strftime(formatted,sizeof(formatted),"%Y-%m-%dT%H:%M:%S",&local);
            cJSON_AddStringToObject(o,"local",formatted);
            cJSON_AddBoolToObject(o,"is_dst",local.tm_isdst>0);
            cJSON_AddNumberToObject(o,"local_seconds",local.tm_hour*3600+local.tm_min*60+local.tm_sec);
        }
    }
    return o;
}
