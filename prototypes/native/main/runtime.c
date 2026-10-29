/* LAN API. Default bench build is memory-only; controller GPIO is USB opt-in. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <unistd.h>
#include "serial_frame.h"
#include "wifi_trace.h"
#include "wifi_ap_trial.h"
#include "sdkconfig.h"
#include "target_board.h"
#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
#include "hal/usb_serial_jtag_ll.h"
#endif
#include "runtime.h"
#include "ota.h"
#include "ota_fence.h"
#include "clock_service.h"
#include "board_io.h"
#include "relay_engine.h"
#include "device_profile.h"
#include "io_backend.h"
#include "esp_app_desc.h"
#include "esp_mac.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_http_server.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "driver/uart.h"
#include "mdns.h"
#include "cJSON.h"

#define MAX_BODY 12288
#define MAX_RELAYS 16
/* Simulation identifiers corresponding to the controllers' board definition.
   Accepting these numbers DOES NOT enable/configure physical GPIO. */
static const int allowed_pins[]=GARDEN_ALLOWED_PINS;
static rule_inputs simulated_inputs;
static nvs_handle_t store;
static SemaphoreHandle_t lock;
static cJSON *relays, *device_profile;
static esp_netif_t *netif;
static atomic_bool wifi_enabled, has_ip;
static atomic_uint disconnects, fail_streak, retry_at, last_reason;
static wifi_trace wifi_history;
static portMUX_TYPE wifi_history_lock=portMUX_INITIALIZER_UNLOCKED;
static engine_stats automation_stats;
static engine_mock mock_outputs;
static io_backend outputs;
static io_gpio_driver gpio_driver;
static char boot_layout[65], armed_layout[65], device_id[13];
static int commit_status=500;
static bool outputs_applied=true, persistence_uncertain;
static engine_time_guard runtime_clock;
static bool use_network_clock;
static char hostname[64]="garden-bench", active_hostname[64]="garden-bench";

static unsigned seconds(void) { return (unsigned)(esp_timer_get_time()/1000000); }
static cJSON *message(const char *text, bool success)
{
    cJSON *o = cJSON_CreateObject();
    cJSON_AddBoolToObject(o, "success", success);
    cJSON_AddStringToObject(o, success ? "message" : "error", text);
    return o;
}
static void put_bool(cJSON *o, const char *key, bool value)
{
    cJSON_DeleteItemFromObject(o, key);
    cJSON_AddBoolToObject(o, key, value);
}
static const char *text(cJSON *o, const char *key)
{
    cJSON *v = cJSON_GetObjectItemCaseSensitive(o, key);
    return cJSON_IsString(v) ? v->valuestring : NULL;
}
static cJSON *parse(const char *body)
{
    /* cJSON's default recursion limit is too large for an embedded task stack.
       Reject nesting beyond 16 before allocating/parsing; honor string escapes. */
    unsigned depth=0;
    bool quoted=false, escaped=false;
    for (const unsigned char *p=(const unsigned char *)body; *p; p++) {
        if (quoted) {
            if (escaped) escaped=false;
            else if (*p=='\\') escaped=true;
            else if (*p=='\"') quoted=false;
        } else if (*p=='\"') quoted=true;
        else if (*p=='{' || *p=='[') { if (++depth>16) return NULL; }
        else if (*p=='}' || *p==']') { if (!depth) return NULL; depth--; }
    }
    if (depth || quoted) return NULL;
    return cJSON_ParseWithOpts(body, NULL, true);
}

#define valid_relays profile_valid_relays
static esp_err_t runtime_write(void *unused,int pin,bool command,bool inverted)
{
    (void)unused;
    return outputs.active?io_backend_write(&outputs,pin,command,inverted):
        engine_mock_write(&mock_outputs,pin,command,inverted);
}
static bool physical_ready(cJSON *profile)
{
    return text(profile,"timezone") && !strcmp(text(profile,"clock_source"),"network") &&
        cJSON_GetArraySize(cJSON_GetObjectItemCaseSensitive(profile,"relays"))>0;
}
static void output_result(cJSON *reply)
{
    cJSON_AddBoolToObject(reply,"outputs_applied",outputs_applied);
    if (!outputs_applied) cJSON_AddStringToObject(reply,"warning","Configuration saved but an output write failed; inspect values and last_error before retrying");
}
static void adopt_profile(cJSON *next,bool reset_source)
{
    const char *zone=text(next,"timezone"),*old_zone=text(device_profile,"timezone");
    bool zone_changed=(zone==NULL)!=(old_zone==NULL) || (zone && old_zone && strcmp(zone,old_zone));
    bool source_changed=!device_profile || strcmp(text(next,"clock_source"),text(device_profile,"clock_source"));
    if (reset_source || source_changed) use_network_clock=!strcmp(text(next,"clock_source"),"network");
    if (reset_source || source_changed || (use_network_clock && zone_changed)) {
        runtime_clock=(engine_time_guard){0};simulated_inputs.time_seconds=-1;simulated_inputs.last_time_seconds=-1;
    }
    cJSON_Delete(device_profile);device_profile=next;
    relays=cJSON_GetObjectItemCaseSensitive(next,"relays");
    snprintf(hostname,sizeof(hostname),"%s",text(next,"hostname"));
}
static uint32_t edit_generation;
/* Caller owns runtime lock. Current values/diagnostics are deliberately excluded. */
static bool current_ota_fence(char out[65])
{
    cJSON *health=ota_status();char layout[65],revision[65];
    const char *state=text(health,"running_state"),*running=text(health,"running_slot"),*boot_slot=text(health,"boot_slot");
    bool valid=health && cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(health,"healthy")) && state && !strcmp(state,"valid") &&
        !wifi_ap_trial_pending() && running && boot_slot && !strcmp(running,boot_slot) && !outputs.cleanup_failed && outputs_applied && !persistence_uncertain && !strcmp(hostname,active_hostname) &&
        io_layout_hash(device_profile,layout) && profile_edit_revision(device_profile,edit_generation,revision);
    bool armed=valid && armed_layout[0] && !strcmp(layout,armed_layout);
    valid=valid && outputs.active==armed && ota_fence_hash(device_id,text(health,"boot_id"),layout,revision,text(health,"elf_sha256"),outputs.active,armed,out);
    cJSON_Delete(health);return valid;
}
bool runtime_ota_reserve(const char *expected_fence)
{
    /* uploading was atomically claimed before taking this lock. Existing commits
       finish first; all later persistent/arming writes reject until cleanup/reset.
       Never hold this lock across image receive or flash streaming. */
    xSemaphoreTake(lock,portMAX_DELAY);
    char current[65];
    bool ok=ota_upload_in_progress() && current_ota_fence(current) &&
        ota_fence_accept(io_gpio_operations()!=NULL,expected_fence,current);
    xSemaphoreGive(lock);return ok;
}
static bool commit_profile(cJSON *next,bool reset_source)
{
    commit_status=500;outputs_applied=true;
    if (ota_upload_in_progress() || persistence_uncertain) {commit_status=503;return false;}
    bool switch_change=outputs.active && !io_live_settings_compatible(device_profile,next);
    if (switch_change && !io_live_switch_settings_compatible(device_profile,next)) {commit_status=409;return false;}
    char next_layout[65],old_layout[65],record[80];
    if (!io_layout_hash(next,next_layout) || !io_layout_hash(device_profile,old_layout)) return false;
    bool rebind=outputs.active && strcmp(next_layout,old_layout);
    /* Never turn a pending explicit disarm back into an arm as an edit side effect. */
    if (rebind && strcmp(old_layout,armed_layout)) {commit_status=409;return false;}
    if (rebind) snprintf(record,sizeof(record),"%s/%s",device_id,next_layout);
    /* Relay GPIO is untouched until persistence succeeds. Input-only edits stage
       new inputs while every relay is manual/current/default OFF; errors restore
       previous inputs or latch uncertainty. Legacy keys stay untouched. */
    engine_mock prepared=mock_outputs;
    if (engine_apply_commands(cJSON_GetObjectItemCaseSensitive(next,"relays"),engine_mock_write,&prepared)!=ESP_OK) return false;
    char *s=cJSON_PrintUnformatted(next);
    if (!s || strlen(s)>=MAX_BODY) {free(s);return false;}
    const char *old_zone=text(device_profile,"timezone");
    if (!clock_service_use_zone(text(next,"timezone"))) {free(s);return false;}
    if (switch_change) {
        esp_err_t input_err=io_backend_reconfigure_switches(&outputs,next,(uint32_t)(esp_timer_get_time()/1000));
        io_backend_sample(&outputs,(uint32_t)(esp_timer_get_time()/1000));
        io_backend_baseline_switches(&outputs,&simulated_inputs);
        if (input_err!=ESP_OK) {
            if (outputs.cleanup_failed) {persistence_uncertain=true;outputs_applied=false;}
            free(s);return false;
        }
    }
    esp_err_t err=nvs_set_str(store,"profile_v1",s);
    if (err==ESP_OK && rebind) err=nvs_set_str(store,"arm_v1",record);
    if (err==ESP_OK) err=nvs_commit(store);
    free(s);
    /* Two NVS keys are NOT a power-fail atomic transaction. A torn pair fails
       closed at boot by exact hash mismatch. On a reported rebind error, block
       further edits/OTA rather than claim RAM proves persisted arming state. */
    if (err!=ESP_OK) {
        if (rebind) persistence_uncertain=true;
        if (switch_change) {
            if (io_backend_reconfigure_switches(&outputs,device_profile,(uint32_t)(esp_timer_get_time()/1000))!=ESP_OK) outputs_applied=false;
            io_backend_sample(&outputs,(uint32_t)(esp_timer_get_time()/1000));
            io_backend_baseline_switches(&outputs,&simulated_inputs);
        }
        clock_service_use_zone(old_zone);return false;
    }
    mock_outputs=prepared;adopt_profile(next,reset_source && !outputs.active);edit_generation++;
    if (rebind) snprintf(armed_layout,sizeof(armed_layout),"%s",next_layout);
    if (outputs.active && !switch_change) outputs_applied=io_backend_apply(&outputs,relays);
    return true;
}
static bool commit_relays(cJSON *next)
{
    commit_status=500;
    if (!valid_relays(next)) return false;
    cJSON *candidate=cJSON_Duplicate(device_profile,true);
    if (!candidate) return false;
    cJSON *copy=cJSON_Duplicate(next,true);
    if (!copy) {cJSON_Delete(candidate);return false;}
    cJSON_ReplaceItemInObjectCaseSensitive(candidate,"relays",copy);
    cJSON *normalized=profile_normalize(candidate);cJSON_Delete(candidate);
    if (!normalized || !commit_profile(normalized,false)) {cJSON_Delete(normalized);return false;}
    cJSON_Delete(next);return true;
}
static void load_relays(void)
{
    size_t size=0;
    if (nvs_get_str(store,"relays",NULL,&size)==ESP_OK && size<=MAX_BODY) {
        char *s=malloc(size);
        if (s && nvs_get_str(store,"relays",s,&size)==ESP_OK) relays=parse(s);
        free(s);
    }
    if (!valid_relays(relays)) {
        cJSON_Delete(relays);
        /* Common valid JSON seed; retain historical S3 pin1, original ESP32 pin4.
           This is memory-only until an independently bound arm record exists. */
        relays=parse("[{\"pin\":4,\"label\":\"SIMULATED relay\",\"rule\":\"return nil\",\"value\":false,\"auto\":false,\"isInverted\":false,\"defaultValue\":false,\"defaultAuto\":false}]");
        if (relays) cJSON_SetNumberValue(cJSON_GetObjectItemCaseSensitive(cJSON_GetArrayItem(relays,0),"pin"),GARDEN_FACTORY_RELAY_PIN);
    }
    cJSON *r;
    cJSON_ArrayForEach(r,relays) {
        put_bool(r,"value",cJSON_IsTrue(cJSON_GetObjectItem(r,"defaultValue")));
        put_bool(r,"auto",cJSON_IsTrue(cJSON_GetObjectItem(r,"defaultAuto")));
        cJSON_DeleteItemFromObject(r,"last_error");
        cJSON_AddNullToObject(r,"last_error");
    }
}
static void load_profile(void)
{
    size_t size=0;esp_err_t err=nvs_get_str(store,"profile_v1",NULL,&size);
    cJSON *next=NULL;
    if (err==ESP_ERR_NVS_NOT_FOUND) {
        cJSON *clock=clock_service_status();next=profile_from_legacy(relays,text(clock,"timezone"));cJSON_Delete(clock);
    } else {
        ESP_ERROR_CHECK(err);ESP_ERROR_CHECK(size>0 && size<=MAX_BODY?ESP_OK:ESP_ERR_INVALID_SIZE);
        char *s=malloc(size);configASSERT(s);
        ESP_ERROR_CHECK(nvs_get_str(store,"profile_v1",s,&size));
        cJSON *raw=parse(s);free(s);next=profile_normalize(raw);cJSON_Delete(raw);
    }
    /* Corrupt/unknown stored profiles are fatal, never replaced with defaults. */
    ESP_ERROR_CHECK(next?ESP_OK:ESP_ERR_INVALID_VERSION);
    cJSON_Delete(relays);relays=NULL;
    ESP_ERROR_CHECK(clock_service_use_zone(text(next,"timezone"))?ESP_OK:ESP_ERR_INVALID_STATE);
    adopt_profile(next,true);snprintf(active_hostname,sizeof(active_hostname),"%s",hostname);
    cJSON *r;cJSON_ArrayForEach(r,relays) {
        put_bool(r,"value",cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"defaultValue")));
        put_bool(r,"auto",cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"defaultAuto")));
        cJSON_AddNullToObject(r,"last_error");
    }
}
static void wifi_record(wifi_trace_kind kind,const uint8_t *bssid,int channel,int rssi,int authmode,int reason,int error)
{
    wifi_trace_event event={.monotonic_ms=(uint64_t)(esp_timer_get_time()/1000),
        .kind=kind,.channel=channel,.rssi=rssi,.authmode=authmode,.reason=reason,.error=error};
    if (bssid) memcpy(event.bssid,bssid,6);
    portENTER_CRITICAL(&wifi_history_lock);
    wifi_trace_append(&wifi_history,event);
    portEXIT_CRITICAL(&wifi_history_lock);
}
static void wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    if (base==WIFI_EVENT && id==WIFI_EVENT_STA_START) {
        wifi_record(WIFI_TRACE_START,NULL,-1,0,-1,0,0);
        atomic_store(&retry_at,seconds());
    } else if (base==WIFI_EVENT && id==WIFI_EVENT_STA_CONNECTED) {
        const wifi_event_sta_connected_t *event=data;
        wifi_record(WIFI_TRACE_LINK_UP,event->bssid,event->channel,0,event->authmode,0,0);
    } else if (base==WIFI_EVENT && id==WIFI_EVENT_STA_DISCONNECTED) {
        const wifi_event_sta_disconnected_t *event=data;
        wifi_record(WIFI_TRACE_DISCONNECT,event->bssid,-1,event->rssi,-1,event->reason,0);
        atomic_store(&has_ip,false);
        atomic_fetch_add(&disconnects,1);
        atomic_store(&last_reason,event->reason);
        unsigned n=atomic_fetch_add(&fail_streak,1);
        unsigned delay=1u<<(n>5?5:n);
        atomic_store(&retry_at,seconds()+delay);
    } else if (base==IP_EVENT && id==IP_EVENT_STA_GOT_IP) {
        atomic_store(&has_ip,true);
        atomic_store(&fail_streak,0);
        wifi_ap_record_t ap;
        if (esp_wifi_sta_get_ap_info(&ap)==ESP_OK)
            wifi_record(WIFI_TRACE_GOT_IP,ap.bssid,ap.primary,ap.rssi,ap.authmode,0,0);
        else wifi_record(WIFI_TRACE_GOT_IP,NULL,-1,0,-1,0,0);
        printf("WIFI_GOT_IP\n"); /* actual address is available via status */
        clock_service_network_ready();
    }
}
static void network_task(void *arg)
{
    (void)arg;
    for (;;) {
        bool was_pending=wifi_ap_trial_pending();
        ESP_ERROR_CHECK(wifi_ap_trial_poll((uint32_t)(esp_timer_get_time()/1000)));
        if (was_pending && !wifi_ap_trial_pending()) {
            atomic_store(&has_ip,false);atomic_store(&fail_streak,0);
            atomic_store(&retry_at,seconds());
        }
        if (!wifi_ap_trial_pending()) ota_heartbeat(1);
        ota_watchdog_fault_checkpoint(1);
        if (atomic_load(&wifi_enabled) && !atomic_load(&has_ip) && seconds()>=atomic_load(&retry_at)) {
            atomic_store(&retry_at,seconds()+35); /* connection-attempt watchdog */
            wifi_record(WIFI_TRACE_ATTEMPT,NULL,-1,0,-1,0,0);
            esp_err_t err=esp_wifi_connect();
            if (err!=ESP_OK) {
                wifi_record(WIFI_TRACE_CONNECT_ERROR,NULL,-1,0,-1,0,err);
                atomic_store(&retry_at,seconds()+5);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
static bool provision(cJSON *o)
{
    const char *ssid=text(o,"ssid"), *password=text(o,"password");
    if (!ssid || !*ssid || strlen(ssid)>32 || !password || strlen(password)>63 ||
        (*password && strlen(password)<8)) return false;
    wifi_config_t cfg={0};
    memcpy(cfg.sta.ssid,ssid,strlen(ssid));
    memcpy(cfg.sta.password,password,strlen(password));
    cfg.sta.pmf_cfg.capable=true;
    if (nvs_set_blob(store,"wifi",&cfg,sizeof(cfg))!=ESP_OK || nvs_commit(store)!=ESP_OK) return false;
    edit_generation++; /* Public edit/OTA fences invalidate without exposing credentials. */
    atomic_store(&wifi_enabled,false);
    esp_wifi_stop();
    atomic_store(&has_ip,false);
    esp_err_t err=esp_wifi_set_config(WIFI_IF_STA,&cfg);
    memset(&cfg,0,sizeof(cfg));
    if (err!=ESP_OK) return false;
    atomic_store(&wifi_enabled,true);
    return esp_wifi_start()==ESP_OK;
}
/* Build-local A/B test only: no profile/credential or SDK default changes.
   Apply after driver initialization/mode selection, before tasks/association. */
static esp_err_t wifi_apply_power_policy(void)
{
#ifdef CONFIG_GARDEN_WIFI_DISABLE_MODEM_SLEEP
    return esp_wifi_set_ps(WIFI_PS_NONE);
#else
    return ESP_OK;
#endif
}
static void wifi_json_bssid(cJSON *o,const char *key,const uint8_t bssid[6])
{
    if (!wifi_trace_bssid_known(bssid)) {cJSON_AddNullToObject(o,key);return;}
    char value[18];snprintf(value,sizeof(value),"%02x:%02x:%02x:%02x:%02x:%02x",
        (unsigned)bssid[0],(unsigned)bssid[1],(unsigned)bssid[2],(unsigned)bssid[3],(unsigned)bssid[4],(unsigned)bssid[5]);
    cJSON_AddStringToObject(o,key,value);
}
static cJSON *wifi_diagnostics(void)
{
    /* Capture under a SHORT dedicated critical section. Never allocate JSON,
       acquire runtime/NVS locks or call SDK/network functions while holding it. */
    wifi_trace snapshot;
    portENTER_CRITICAL(&wifi_history_lock);snapshot=wifi_history;portEXIT_CRITICAL(&wifi_history_lock);
    cJSON *o=cJSON_CreateObject(),*events=cJSON_CreateArray();
    cJSON_AddNumberToObject(o,"format_version",1);
    cJSON_AddNumberToObject(o,"uptime_ms",(double)(esp_timer_get_time()/1000));
    cJSON_AddNumberToObject(o,"capacity",WIFI_TRACE_CAPACITY);
    cJSON_AddNumberToObject(o,"total_events",(double)snapshot.written);
    cJSON_AddNumberToObject(o,"overwritten_events",(double)(snapshot.written-wifi_trace_count(&snapshot)));
    cJSON_AddBoolToObject(o,"volatile_per_boot",true);
    cJSON *health=ota_status();
    cJSON_AddStringToObject(o,"boot_id",text(health,"boot_id"));cJSON_Delete(health);
    for (unsigned i=0;i<wifi_trace_count(&snapshot);i++) {
        const wifi_trace_event *e=wifi_trace_at(&snapshot,i);cJSON *row=cJSON_CreateObject();
        cJSON_AddNumberToObject(row,"sequence",(double)e->sequence);
        cJSON_AddNumberToObject(row,"uptime_ms",(double)e->monotonic_ms);
        cJSON_AddStringToObject(row,"event",wifi_trace_name(e->kind));
        wifi_json_bssid(row,"bssid",e->bssid);
        if (e->channel>=0) cJSON_AddNumberToObject(row,"channel",e->channel);else cJSON_AddNullToObject(row,"channel");
        if (e->rssi<0) cJSON_AddNumberToObject(row,"rssi",e->rssi);else cJSON_AddNullToObject(row,"rssi");
        if (e->authmode>=0) cJSON_AddNumberToObject(row,"authmode",e->authmode);else cJSON_AddNullToObject(row,"authmode");
        cJSON_AddNumberToObject(row,"reason",e->reason);cJSON_AddNumberToObject(row,"sdk_error",e->error);
        cJSON_AddItemToArray(events,row);
    }
    cJSON_AddItemToObject(o,"events",events);return o;
}
static cJSON *wifi_status(void)
{
    cJSON *o=cJSON_CreateObject();
    cJSON_AddBoolToObject(o,"sta_connected",atomic_load(&has_ip));
    cJSON_AddBoolToObject(o,"provisioned",atomic_load(&wifi_enabled));
    cJSON_AddBoolToObject(o,"ap_active",false);
    wifi_ap_record_t ap;
    if (esp_wifi_sta_get_ap_info(&ap)==ESP_OK) {
        char ssid[33]; memcpy(ssid,ap.ssid,32); ssid[32]=0;
        cJSON_AddStringToObject(o,"sta_ssid",ssid);
        cJSON_AddNumberToObject(o,"sta_rssi",ap.rssi);
        wifi_json_bssid(o,"sta_bssid",ap.bssid);
        cJSON_AddNumberToObject(o,"sta_channel",ap.primary);
        cJSON_AddNumberToObject(o,"sta_authmode",ap.authmode);
    }
    wifi_ps_type_t ps;
    if (esp_wifi_get_ps(&ps)==ESP_OK) cJSON_AddNumberToObject(o,"power_save_mode",ps);
    esp_netif_ip_info_t ip;
    if (atomic_load(&has_ip) && esp_netif_get_ip_info(netif,&ip)==ESP_OK) {
        char address[16]; snprintf(address,sizeof(address),IPSTR,IP2STR(&ip.ip));
        cJSON_AddStringToObject(o,"sta_ip",address);
    }
    cJSON_AddBoolToObject(o,"single_ap_trial_enabled",wifi_ap_trial_enabled());
    cJSON_AddBoolToObject(o,"single_ap_trial_pending",wifi_ap_trial_pending());
    cJSON_AddNumberToObject(o,"disconnect_count",atomic_load(&disconnects));
    cJSON_AddNumberToObject(o,"last_disconnect_reason",atomic_load(&last_reason));
    return o;
}
static void status_row(cJSON *rows,const char *key,double value)
{
    cJSON *r=cJSON_CreateObject();
    cJSON_AddStringToObject(r,"key",key); cJSON_AddNumberToObject(r,"value",value);
    cJSON_AddItemToArray(rows,r);
}

static bool read_inputs(cJSON *o,rule_inputs *in)
{
    if (!cJSON_IsObject(o)) return false;
    const char *numbers[]={"temperature","last_temperature","humidity","last_humidity","light_level","last_light_level"};
    double *dest[]={&in->temperature,&in->last_temperature,&in->humidity,&in->last_humidity,&in->light,&in->last_light};
    const char *booleans[]={"switch_state","last_switch_state","reset_switch_state","last_reset_switch_state"};
    bool *flags[]={&in->switch_state,&in->last_switch_state,&in->reset_switch,&in->last_reset_switch};
    const char *times[]={"time_seconds","last_time_seconds"};
    int *clocks[]={&in->time_seconds,&in->last_time_seconds};
    cJSON *v;
    cJSON_ArrayForEach(v,o) {
        bool found=false;
        for (unsigned i=0;i<6;i++) if (!strcmp(v->string,numbers[i])) {
            if (!cJSON_IsNull(v) && (!cJSON_IsNumber(v) || !isfinite(v->valuedouble))) return false;
            *dest[i]=cJSON_IsNull(v)?NAN:v->valuedouble;found=true;
        }
        for (unsigned i=0;i<4;i++) if (!strcmp(v->string,booleans[i])) {
            if (!cJSON_IsBool(v)) return false;
            *flags[i]=cJSON_IsTrue(v);found=true;
        }
        for (unsigned i=0;i<2;i++) if (!strcmp(v->string,times[i])) {
            if (!cJSON_IsNull(v) && (!cJSON_IsNumber(v) || v->valuedouble!=v->valueint || v->valueint<0 || v->valueint>=86400)) return false;
            *clocks[i]=cJSON_IsNull(v)?-1:v->valueint;found=true;
        }
        if (!found) return false;
    }
    return true;
}

static bool read_clock(cJSON *o,engine_clock *clock)
{
    cJSON *valid=cJSON_GetObjectItemCaseSensitive(o,"valid");
    cJSON *mono=cJSON_GetObjectItemCaseSensitive(o,"monotonic_ms");
    if (!cJSON_IsBool(valid) || !cJSON_IsNumber(mono) || mono->valuedouble<0 ||
        mono->valuedouble>4102444800000.0 || floor(mono->valuedouble)!=mono->valuedouble) return false;
    clock->valid=cJSON_IsTrue(valid);clock->monotonic_ms=(int64_t)mono->valuedouble;
    if (!clock->valid) return true;
    cJSON *utc=cJSON_GetObjectItemCaseSensitive(o,"unix_seconds");
    cJSON *local=cJSON_GetObjectItemCaseSensitive(o,"local_seconds");
    if (!cJSON_IsNumber(utc) || utc->valuedouble<1577836800 || utc->valuedouble>4102444800.0 ||
        floor(utc->valuedouble)!=utc->valuedouble || !cJSON_IsNumber(local) ||
        local->valuedouble!=local->valueint || local->valueint<0 || local->valueint>=86400) return false;
    clock->unix_seconds=(int64_t)utc->valuedouble;clock->local_seconds=local->valueint;return true;
}
static cJSON *run_engine_trace(const char *body,int *status)
{
    cJSON *o=parse(body),*array=cJSON_GetObjectItemCaseSensitive(o,"relays");
    cJSON *frames=cJSON_GetObjectItemCaseSensitive(o,"frames");
    int count=cJSON_GetArraySize(frames),channels=cJSON_GetArraySize(array);
    if (!valid_relays(array) || !cJSON_IsArray(frames) || count<1 || count>16 ||
        count*(channels?channels:1)>64) {
        cJSON_Delete(o);*status=400;return message("Trace requires valid relays, 1..16 frames and <=64 relay outcomes",false);
    }
    cJSON *copy=cJSON_Duplicate(array,true),*results=cJSON_CreateArray();
    if (!copy || !results) {cJSON_Delete(copy);cJSON_Delete(results);cJSON_Delete(o);*status=500;return message("Out of memory",false);}
    engine_mock mock={0};engine_stats stats={0};engine_time_guard guard={0};
    rule_inputs in=rule_inputs_default();engine_apply_commands(copy,engine_mock_write,&mock);
    int64_t deadline=esp_timer_get_time()+500000;
    const char *failure=NULL;
    cJSON *frame;
    cJSON_ArrayForEach(frame,frames) {
        cJSON *inputs=cJSON_GetObjectItemCaseSensitive(frame,"inputs");
        if (!read_inputs(inputs,&in)) {failure="Invalid frame inputs";break;}
        cJSON *clock=cJSON_GetObjectItemCaseSensitive(frame,"clock");
        if (clock) {
            engine_clock sample={0};
            if (!read_clock(clock,&sample)) {failure="Invalid frame clock";break;}
            engine_prepare_clock(&guard,&sample,&in);
        }
        cJSON *failed=cJSON_GetObjectItemCaseSensitive(frame,"fail_pin");
        mock.fail_pin=0;
        if (failed) {
            if (!cJSON_IsNumber(failed) || failed->valuedouble!=failed->valueint ||
                (failed->valueint!=0 && !io_pin_allowed(failed->valueint))) {failure="Invalid injected output failure";break;}
            mock.fail_pin=failed->valueint;
        }
        engine_tick(copy,&in,engine_mock_write,&mock,&stats);
        cJSON *snapshot=cJSON_CreateObject(),*outputs=cJSON_CreateArray();
        cJSON *r;
        cJSON_ArrayForEach(r,copy) {
            int pin=cJSON_GetObjectItemCaseSensitive(r,"pin")->valueint;
            cJSON *item=cJSON_CreateObject();cJSON_AddNumberToObject(item,"pin",pin);
            cJSON_AddBoolToObject(item,"value",cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"value")));
            cJSON_AddBoolToObject(item,"level",mock.levels[pin]);
            cJSON *err=cJSON_GetObjectItemCaseSensitive(r,"last_error");
            if (cJSON_IsString(err)) cJSON_AddStringToObject(item,"error",err->valuestring);
            else cJSON_AddNullToObject(item,"error");
            cJSON_AddItemToArray(outputs,item);
        }
        cJSON_AddItemToObject(snapshot,"outputs",outputs);
        cJSON_AddNumberToObject(snapshot,"last_time_seconds",in.last_time_seconds);
        cJSON_AddItemToArray(results,snapshot);
        engine_advance_inputs(&in);
        if (esp_timer_get_time()>deadline) {failure="Trace exceeded cooperative 500ms budget";*status=408;break;}
    }
    cJSON_Delete(copy);cJSON_Delete(o);
    if (failure) {cJSON_Delete(results);if (*status!=408) *status=400;return message(failure,false);}
    cJSON *out=message("Shared engine executed against memory-only outputs; runtime state unchanged",true);
    cJSON_AddItemToObject(out,"frames",results);
    cJSON_AddNumberToObject(out,"evaluations",stats.evaluations);
    cJSON_AddNumberToObject(out,"writes",stats.writes);
    cJSON_AddNumberToObject(out,"errors",stats.errors);
    cJSON_AddNumberToObject(out,"discontinuities",guard.discontinuities);return out;
}

/* Called under lock, identically by HTTP and the USB test transport. */
static cJSON *dispatch(const char *method,const char *path,const char *body,int *status)
{
    *status=200;
    if (!strcmp(method,"GET")) {
        if (!strcmp(path,"/api/profile")) return profile_normalize(device_profile);
        if (!strcmp(path,"/api/profile/edit")) {
            char hash[65];
            if (!profile_edit_revision(device_profile,edit_generation,hash)) {*status=500;return message("Cannot allocate edit snapshot",false);}
            cJSON *out=ota_status(),*profile=profile_normalize(device_profile);
            if (!out || !profile || !cJSON_AddStringToObject(out,"revision",hash) || !cJSON_AddItemToObject(out,"profile",profile)) {
                cJSON_Delete(profile);cJSON_Delete(out);*status=500;return message("Cannot allocate edit snapshot",false);
            }
            return out;
        }
        if (!strcmp(path,"/api/io/status")) {
            cJSON *o=cJSON_CreateObject();char hash[65];
            cJSON_AddStringToObject(o,"device_id",device_id);
            cJSON_AddBoolToObject(o,"gpio_compiled",io_gpio_operations()!=NULL);
            cJSON_AddBoolToObject(o,"gpio_active",outputs.active);
            cJSON_AddBoolToObject(o,"cleanup_failed",outputs.cleanup_failed);
            cJSON_AddBoolToObject(o,"backend_software_tests_passed",true);
            bool valid=io_layout_hash(device_profile,hash);
            if (valid) cJSON_AddStringToObject(o,"layout_hash",hash);
            cJSON_AddBoolToObject(o,"armed_for_saved_layout",valid && armed_layout[0] && !strcmp(hash,armed_layout));
            cJSON_AddBoolToObject(o,"persistence_uncertain",persistence_uncertain);
            cJSON_AddBoolToObject(o,"outputs_applied",outputs_applied);
            cJSON_AddStringToObject(o,"activation","controller build + matching USB arm record + reboot");
            return o;
        }
        if (!strcmp(path,"/api/config")) {
            cJSON *o=message(outputs.active?"GPIO controller; reported values are last successful commands":"All outputs memory-only",true);
            cJSON_AddStringToObject(o,"hostname",hostname);
            cJSON_AddStringToObject(o,"active_hostname",active_hostname);
            cJSON_AddStringToObject(o,"device_role",io_gpio_operations()?"relay-controller":"development-bench");
            cJSON_AddBoolToObject(o,"live_relay_settings",true);
            cJSON_AddBoolToObject(o,"wifi_diagnostics",true);
            cJSON_AddBoolToObject(o,"restart_required",strcmp(hostname,active_hostname)!=0);
            cJSON_AddStringToObject(o,"board",io_gpio_operations()?GARDEN_TARGET_NAME "-controller":GARDEN_TARGET_NAME "-bench");
            cJSON_AddStringToObject(o,"chip_target",GARDEN_TARGET_NAME);
            cJSON_AddStringToObject(o,"board_name",outputs.active?"ESP32-S3 relay controller":"ESP32-S3 simulated outputs");
            cJSON_AddStringToObject(o,"rule_language","lua");
            cJSON_AddBoolToObject(o,"atomic_profile_edit",true);
            cJSON_AddBoolToObject(o,"guarded_ota",true);
            cJSON_AddBoolToObject(o,"simulated",!outputs.active); return o;
        }
        if (!strcmp(path,"/api/wifi/status")) return wifi_status();
        if (!strcmp(path,"/api/wifi/diagnostics")) return wifi_diagnostics();
        if (!strcmp(path,"/api/ota/status")) return ota_status();
        if (!strcmp(path,"/api/ota/fence")) {
            char fence[65];
            if (ota_upload_in_progress() || !current_ota_fence(fence)) {*status=409;return message("OTA fence unavailable: inspect health, boot selection, deferred identity and arming state",false);}
            cJSON *out=message("Public OTA consistency token; not authentication",true);
            cJSON_AddStringToObject(out,"fence",fence);return out;
        }
        if (!strcmp(path,"/api/watchdog/status")) return ota_watchdog_status();
        if (!strcmp(path,"/api/time/status")) {
            cJSON *o=clock_service_status();
            put_bool(o,"feeds_simulated_rules",use_network_clock);return o;
        }
        if (!strcmp(path,"/api/engine/status")) {
            cJSON *o=cJSON_CreateObject(),*levels=cJSON_CreateArray();
            cJSON_AddStringToObject(o,"backend",outputs.active?"gpio":"memory-only");
            cJSON_AddStringToObject(o,"clock_source",use_network_clock?"network":"manual");
            cJSON_AddStringToObject(o,"schedule_policy","edge_no_catchup");
            cJSON_AddNumberToObject(o,"clock_discontinuities",runtime_clock.discontinuities);
            cJSON_AddNumberToObject(o,"evaluations",automation_stats.evaluations);
            cJSON_AddNumberToObject(o,"automation_writes",automation_stats.writes);
            cJSON_AddNumberToObject(o,"rule_or_output_errors",automation_stats.errors);
            cJSON *r;
            cJSON_ArrayForEach(r,relays) {
                int pin=cJSON_GetObjectItemCaseSensitive(r,"pin")->valueint;
                cJSON *item=cJSON_CreateObject();cJSON_AddNumberToObject(item,"pin",pin);
                cJSON_AddBoolToObject(item,"level",outputs.active?relay_gpio_level(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"value")),cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r,"isInverted"))):mock_outputs.levels[pin]);cJSON_AddItemToArray(levels,item);
            }
            cJSON_AddItemToObject(o,"electrical_levels",levels);return o;
        }
        if (!strcmp(path,"/api/time/zones")) return clock_service_zones();
        if (!strcmp(path,"/api/bench/io-status")) {
            cJSON *o=board_io_status();put_bool(o,"runtime_drives_gpio",outputs.active);return o;
        }
        if (!strcmp(path,"/api/status")) {
            cJSON *o=cJSON_CreateArray();
            status_row(o,"uptime_seconds",seconds());
            status_row(o,"reset_reason",esp_reset_reason());
            status_row(o,"free_heap",esp_get_free_heap_size());
            status_row(o,"minimum_free_heap",esp_get_minimum_free_heap_size());
            status_row(o,"wifi_disconnects",atomic_load(&disconnects));
            status_row(o,"rule_evaluations",automation_stats.evaluations);
            status_row(o,"simulated_outputs",!outputs.active); return o;
        }
        if (!strcmp(path,"/api/sensors")) {
            cJSON *o=cJSON_CreateObject();
            cJSON_AddNumberToObject(o,"temperature",simulated_inputs.temperature);
            cJSON_AddNumberToObject(o,"humidity",simulated_inputs.humidity);
            cJSON_AddNumberToObject(o,"light_level",simulated_inputs.light);
            cJSON_AddBoolToObject(o,"switch_state",simulated_inputs.switch_state);
            cJSON_AddBoolToObject(o,"reset_switch_state",simulated_inputs.reset_switch);
            if (simulated_inputs.time_seconds<0) cJSON_AddNullToObject(o,"time_seconds");
            else cJSON_AddNumberToObject(o,"time_seconds",simulated_inputs.time_seconds);
            cJSON_AddBoolToObject(o,"simulated",!outputs.active);return o;
        }
        if (!strcmp(path,"/api/relays/config")) {
            cJSON *o=cJSON_CreateObject();
            cJSON_AddNumberToObject(o,"count",cJSON_GetArraySize(relays));
            cJSON_AddItemToObject(o,"relays",cJSON_Duplicate(relays,true));
            cJSON_AddBoolToObject(o,"simulated",!outputs.active); return o;
        }
        if (!strcmp(path,"/api/gpio/available")) {
            cJSON *o=cJSON_CreateObject();
            for (unsigned i=0;i<sizeof(allowed_pins)/sizeof(allowed_pins[0]);i++) {
                char key[8];snprintf(key,sizeof(key),"%d",allowed_pins[i]);
                cJSON_AddStringToObject(o,key,outputs.active?"controller GPIO identifier; input assignments reserve pins":"simulated GPIO identifier; no output driven");
            }
            return o;
        }
    } else if (!strcmp(method,"POST")) {
        if (!strcmp(path,"/api/profile/import") || !strcmp(path,"/api/profile/patch") || !strcmp(path,"/api/relays/config") ||
            !strcmp(path,"/api/relays/control") || !strcmp(path,"/api/time/config")) {
            if (ota_upload_in_progress() || wifi_ap_trial_pending()) {*status=503;return message("OTA reservation or Wi-Fi trial active; no persistent edit applied",false);}
            cJSON *health=ota_status();
            const char *state=text(health,"running_state");
            bool ready=cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(health,"healthy")) && state && !strcmp(state,"valid");
            cJSON_Delete(health);
            if (!ready) {*status=503;return message("Wait for locally validated boot before changing persistent configuration",false);}
        }
        if (!strcmp(path,"/api/profile/patch")) {
            cJSON *request=parse(body);unsigned count=0;cJSON *field;cJSON_ArrayForEach(field,request) count++;
            const char *expected=text(request,"expected_revision"),*boot=text(request,"expected_boot_id");
            cJSON *changes=cJSON_GetObjectItemCaseSensitive(request,"changes");
            if (!cJSON_IsObject(request) || count!=3 || !expected || strlen(expected)!=64 || !boot || strlen(boot)!=16 || !changes) {
                cJSON_Delete(request);*status=400;return message("expected_revision, expected_boot_id and changes required",false);
            }
            char hash[65];cJSON *health=ota_status();
            bool revision=profile_edit_revision(device_profile,edit_generation,hash);
            const char *actual_boot=text(health,"boot_id");
            bool matches=revision && actual_boot && !strcmp(expected,hash) && !strcmp(boot,actual_boot);
            cJSON_Delete(health);
            if (!matches) {cJSON_Delete(request);*status=revision?409:500;return message("Edit conflict or reboot; inspect fresh state before editing again",false);}
            cJSON *next=profile_edit_merge(device_profile,changes);cJSON_Delete(request);
            if (!next) {*status=400;return message("Invalid partial update, relay identity, pin conflict or unsupported setting",false);}
            if (!commit_profile(next,false)) {cJSON_Delete(next);*status=commit_status;return message("Partial update rejected; relay/clock changes, switch edits without all-manual-OFF, pending disarm or persistence failure require review",false);}
            cJSON *out=message("Partial update persisted; unrelated current outputs preserved",true);
            if (profile_edit_revision(device_profile,edit_generation,hash)) cJSON_AddStringToObject(out,"revision",hash);
            cJSON_AddBoolToObject(out,"restart_required",strcmp(hostname,active_hostname)!=0);
            output_result(out);return out;
        }
        if (!strcmp(path,"/api/profile/import") || !strcmp(path,"/api/profile/validate")) {
            cJSON *raw=parse(body),*next=profile_normalize(raw);cJSON_Delete(raw);
            if (!next) {*status=400;return message("Invalid v1 profile, pin conflict, unsupported sensor/clock setting, or insufficient memory",false);}
            bool restart=strcmp(text(next,"hostname"),active_hostname)!=0;
            if (!strcmp(path,"/api/profile/validate")) {
                char hash[65];bool hashed=io_layout_hash(next,hash);
                cJSON_Delete(next);
                if (!hashed) {*status=500;return message("Cannot allocate layout validation",false);}
                cJSON *out=message("Profile validated without applying settings or hardware",true);
                cJSON_AddStringToObject(out,"layout_hash",hash);
                cJSON_AddBoolToObject(out,"restart_required",restart);return out;
            }
            cJSON *health=ota_status();bool healthy=cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(health,"healthy"));cJSON_Delete(health);
            if (!healthy) {cJSON_Delete(next);*status=503;return message("Wait for local boot health before importing a profile",false);}
            if (!commit_profile(next,true)) {cJSON_Delete(next);*status=commit_status;return message("Profile rejected or persistence failed; pin/input/clock changes require isolated maintenance",false);}
            cJSON *out=message(outputs.active?"Controller profile saved; inspect output results":"Profile saved; outputs remain memory-only",true);
            cJSON_AddBoolToObject(out,"restart_required",restart);output_result(out);return out;
        }
        if (!strcmp(path,"/api/bench/backend-selftest")) {
            bool ok=io_backend_selftests();if (!ok) *status=500;
            return message(ok?"Resource lifecycle, faults and cleanup passed against RAM driver only":"Backend software tests failed",ok);
        }
        if (!strcmp(path,"/api/bench/engine-run")) return run_engine_trace(body,status);
        if (!strcmp(path,"/api/bench/clock-source")) {
            if (outputs.active) {*status=409;return message("Active controller owns the network clock",false);}
            cJSON *o=parse(body);const char *source=text(o,"source");
            bool ok=source && (!strcmp(source,"network") || !strcmp(source,"manual"));
            if (ok) {
                use_network_clock=!strcmp(source,"network");runtime_clock=(engine_time_guard){0};
                simulated_inputs.time_seconds=-1;simulated_inputs.last_time_seconds=-1;
            }
            cJSON_Delete(o);if (!ok) *status=400;
            return message(ok?"Bench clock source changed; no GPIO enabled":"source must be network or manual",ok);
        }
        if (!strcmp(path,"/api/relays/control")) {
            cJSON *o=parse(body),*state=cJSON_GetObjectItemCaseSensitive(o,"state");
            const char *label=text(o,"label");
            if (!label || !cJSON_IsBool(state)) {cJSON_Delete(o);*status=400;return message("label and boolean state required",false);}
            cJSON *next=cJSON_Duplicate(relays,true),*r;bool found=false;
            cJSON_ArrayForEach(r,next) if (text(r,"label") && !strcmp(text(r,"label"),label)) {
                put_bool(r,"value",cJSON_IsTrue(state));put_bool(r,"auto",false);found=true;break;
            }
            cJSON_Delete(o);
            if (!found) {cJSON_Delete(next);*status=404;return message("Relay not found",false);}
            if (!commit_relays(next)) {cJSON_Delete(next);*status=commit_status;return message("Cannot persist manual control",false);}
            cJSON *out=message("Relay updated; automatic mode disabled",true);
            cJSON_AddStringToObject(out,"status","success");output_result(out);return out;
        }
        if (!strcmp(path,"/api/bench/io-plan")) {
            cJSON *o=parse(body);
            cJSON *out=board_io_plan(cJSON_GetObjectItemCaseSensitive(o,"relays"),
                                     cJSON_GetObjectItemCaseSensitive(o,"sensor_pins"));
            cJSON_Delete(o);
            if (!out) { *status=400;return message("Invalid/conflicting pins, incomplete I2C pair, or unsupported optional sensor",false); }
            return out; /* No hardware configured, no settings persisted. */
        }
        if (!strcmp(path,"/api/bench/local-time")) {
            cJSON *o=parse(body),*stamp=cJSON_GetObjectItemCaseSensitive(o,"unix_seconds");
            bool ok=cJSON_IsNumber(stamp) && isfinite(stamp->valuedouble) &&
                stamp->valuedouble>=1577836800 && stamp->valuedouble<=4102444800 &&
                floor(stamp->valuedouble)==stamp->valuedouble;
            cJSON *out=ok?clock_service_view_at((long long)stamp->valuedouble):NULL;
            cJSON_Delete(o);
            if (!out) { *status=400;return message("Confirmed timezone and integral timestamp from 2020..2100 required",false); }
            return out; /* Pure conversion: never changes system clock or simulation. */
        }
        if (!strcmp(path,"/api/time/config")) {
            cJSON *o=parse(body),*zone=cJSON_GetObjectItemCaseSensitive(o,"timezone");
            cJSON *candidate=cJSON_Duplicate(device_profile,true);
            bool ok=candidate && (cJSON_IsNull(zone) || cJSON_IsString(zone));
            if (ok) {
                cJSON *copy=cJSON_Duplicate(zone,true);
                ok=copy && cJSON_ReplaceItemInObjectCaseSensitive(candidate,"timezone",copy);
            }
            cJSON *next=ok?profile_normalize(candidate):NULL;cJSON_Delete(candidate);
            bool valid=next!=NULL;
            ok=valid && commit_profile(next,false);
            if (!ok) cJSON_Delete(next);
            cJSON_Delete(o);
            if (!ok) *status=valid?commit_status:400;
            cJSON *out=message(ok?"Timezone saved; inspect clock/engine status":"Unsupported timezone, active layout lock or persistence failure",ok);
            if (ok) output_result(out);
            return out;
        }
        if (!strcmp(path,"/api/bench/evaluate")) {
            cJSON *o=parse(body);
            const char *rule=text(o,"rule");
            rule_inputs in=rule_inputs_default();
            if (!rule || !read_inputs(cJSON_GetObjectItemCaseSensitive(o,"inputs"),&in)) {
                cJSON_Delete(o);*status=400;return message("rule and valid snapshot inputs required",false);
            }
            char error[160]="";size_t peak;
            int result=evaluate_inputs(rule,&in,error,sizeof(error),&peak);
            cJSON *out=message(result==-2?error:"Snapshot evaluated; live/simulated outputs unchanged",result!=-2);
            cJSON_AddNumberToObject(out,"result",result);
            cJSON_AddNumberToObject(out,"lua_peak",peak);
            cJSON_Delete(o);return out;
        }
        if (!strcmp(path,"/api/bench/inputs")) {
            if (outputs.active) {*status=409;return message("Active controller inputs are hardware-owned",false);}
            cJSON *o=parse(body);rule_inputs next=simulated_inputs;
            bool ok=read_inputs(o,&next);
            if (use_network_clock && (cJSON_HasObjectItem(o,"time_seconds") || cJSON_HasObjectItem(o,"last_time_seconds"))) {
                ok=false;
            }
            cJSON_Delete(o);
            if (!ok) { *status=400;return message("Invalid simulated inputs",false); }
            simulated_inputs=next;return message("Simulated inputs updated",true);
        }
        if (!strcmp(path,"/api/validate-rule")) {
            char error[160]=""; size_t peak;
            int result=evaluate_inputs(body,&simulated_inputs,error,sizeof(error),&peak);
            return message(result==-2?error:"Valid Lua rule against current snapshot; no outputs changed",result!=-2);
        }
        if (!strcmp(path,"/api/relays/config")) {
            cJSON *o=parse(body), *array=cJSON_GetObjectItemCaseSensitive(o,"relays");
            if (!valid_relays(array)) {
                cJSON_Delete(o); *status=400;
                return message("Expected up to 16 unique allowed GPIO identifiers, labels, boolean fields and Lua rule <=2048 bytes",false);
            }
            cJSON *next=cJSON_Duplicate(array,true);
            if (!commit_relays(next)) {
                cJSON_Delete(next); cJSON_Delete(o); *status=commit_status; return message("Cannot persist configuration; live pin/default/clock changes require disarm/reboot",false);
            }
            cJSON_Delete(o);
            cJSON *out=message("Saved relay configuration",true);output_result(out);return out;
        }
    }
    *status=404; return message("Endpoint not implemented in bench prototype",false);
}
static esp_err_t http_api(httpd_req_t *req)
{
    if (req->content_len>MAX_BODY) {
        httpd_resp_set_status(req,"413 Payload Too Large");
        httpd_resp_set_type(req,"application/json");
        httpd_resp_set_hdr(req,"Connection","close");
        httpd_resp_sendstr(req,"{\"error\":\"body too large\"}");
        /* Brief bounded discard lets ordinary small oversize clients receive the
           error before TCP close (unread RX can cause RST). Never ask SDK cleanup
           to purge the whole declared stream. One blocking read can add its
           configured socket timeout to this cooperative budget. */
        char discard[512];size_t left=req->content_len<16384?req->content_len:16384;
        int64_t until=esp_timer_get_time()+250000;
        while (left && esp_timer_get_time()<until) {
            int n=httpd_req_recv(req,discard,left<sizeof(discard)?left:sizeof(discard));
            if (n<=0) break;
            left-=n;
        }
        return ESP_FAIL;
    }
    char *body=calloc(req->content_len+1,1);
    if (!body) return ESP_FAIL;
    size_t received=0;int64_t receive_deadline=esp_timer_get_time()+5000000;
    while (received<req->content_len) {
        int n=httpd_req_recv(req,body+received,req->content_len-received);
        if (n<=0) { free(body); return ESP_FAIL; }
        received+=n;
        if (esp_timer_get_time()>receive_deadline) {
            /* A per-recv socket timeout alone permits an indefinitely trickling
               body to monopolize the HTTP worker. Never dispatch partial data. */
            free(body);httpd_resp_set_status(req,"408 Request Timeout");
            httpd_resp_set_type(req,"application/json");
            httpd_resp_set_hdr(req,"Connection","close");
            httpd_resp_sendstr(req,"{\"error\":\"request body deadline exceeded\"}");
            return ESP_FAIL; /* Close the socket: unread body must not become a request. */
        }
    }
    /* Reject embedded NULs rather than silently interpreting a prefix. */
    if (strlen(body)!=req->content_len) {
        free(body); httpd_resp_set_status(req,"400 Bad Request"); return httpd_resp_sendstr(req,"{}");
    }
    xSemaphoreTake(lock,portMAX_DELAY);
    int status;
    cJSON *o=dispatch(req->method==HTTP_GET?"GET":"POST",req->uri,body,&status);
    char *out=cJSON_PrintUnformatted(o); cJSON_Delete(o);
    xSemaphoreGive(lock); free(body);
    httpd_resp_set_type(req,"application/json");
    if (status==400) httpd_resp_set_status(req,"400 Bad Request");
    if (status==404) httpd_resp_set_status(req,"404 Not Found");
    if (status==408) httpd_resp_set_status(req,"408 Request Timeout");
    if (status==409) httpd_resp_set_status(req,"409 Conflict");
    if (status==500) httpd_resp_set_status(req,"500 Internal Server Error");
    if (status==503) httpd_resp_set_status(req,"503 Service Unavailable");
    esp_err_t err=out?httpd_resp_sendstr(req,out):ESP_FAIL;
    free(out); return err;
}
static cJSON *usb_io_mode(cJSON *req,bool arm,int *status)
{
    if (arm && wifi_ap_trial_enabled()) {*status=400;return message("Temporary trial firmware cannot arm; restore normal image first",false);}
    if (ota_upload_in_progress() || wifi_ap_trial_pending() || persistence_uncertain) {*status=503;return message("OTA/trial reservation or persistence uncertainty; no arming mutation applied",false);}
    if (!io_gpio_operations()) {*status=400;return message("GPIO activation is not compiled into bench firmware",false);}
    cJSON *health=ota_status();const char *state=text(health,"running_state");
    bool ready=cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(health,"healthy")) && state && !strcmp(state,"valid");
    const char *actual_boot=text(health,"boot_id"),*expected_boot=text(req,"boot_id");
    bool same_boot=actual_boot && expected_boot && !strcmp(actual_boot,expected_boot);
    cJSON_Delete(health);
    if (!ready) {*status=503;return message("Wait for locally validated boot",false);}
    if (!same_boot) {*status=409;return message("Controller rebooted or expected boot ID missing; no arming mutation applied",false);}
    const char *confirm=text(req,"confirm"),*expected=text(req,"layout_hash"),*chip=text(req,"device_id");char hash[65];
    const char *phrase=arm?"enable relay outputs after reboot":"disable relay outputs after reboot";
    if (!chip || strcmp(chip,device_id) || !confirm || strcmp(confirm,phrase) || !expected || !io_layout_hash(device_profile,hash) || strcmp(hash,expected)) {
        *status=400;return message("Exact USB confirmation, device ID and current saved layout hash required",false);
    }
    if (arm && (outputs.active || !physical_ready(device_profile))) {
        *status=409;return message("Arm requires inactive GPIO, configured network clock/timezone and at least one relay",false);
    }
    char record[80];snprintf(record,sizeof(record),"%s/%s",device_id,hash);
    esp_err_t err=arm?nvs_set_str(store,"arm_v1",record):nvs_erase_key(store,"arm_v1");
    if (err==ESP_ERR_NVS_NOT_FOUND && !arm) err=ESP_OK;
    if (err==ESP_OK) err=nvs_commit(store);
    if (err!=ESP_OK) {*status=500;return message("Arming state persistence uncertain; inspect via USB before retrying",false);}
    edit_generation++; /* Even an explicit no-op disarm invalidates prior reviews. */
    snprintf(armed_layout,sizeof(armed_layout),"%s",arm?hash:"");
    cJSON *out=message(arm?"Armed for this saved layout AFTER reboot":"Disarmed AFTER reboot; current outputs remain unchanged until then",true);
    cJSON_AddBoolToObject(out,"restart_required",true);cJSON_AddBoolToObject(out,"gpio_active",outputs.active);return out;
}
static int native_setup_read(unsigned char *ch)
{
#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
    /* Only this task consumes native CDC RX. The SDK secondary console is TX
     * only; its nonblocking VFS read checks an uninstalled driver's ring buffer,
     * not the hardware FIFO. Poll the bounded FIFO directly, without installing
     * an ISR/driver or changing the UART logging/secondary output path. */
    return usb_serial_jtag_ll_read_rxfifo(ch,1);
#else
    (void)ch;return 0;
#endif
}
static void serial_task(void *arg)
{
    (void)arg;
    /* Keep UART0 as primary logging/setup. Use the existing secondary VFS for
     * native replies and FIFO polling for native input; no replacement console,
     * extra driver/ISR, GPIO change or second unmonitored task is needed. */
    int ports=1;
    FILE *reply[2]={fopen("/dev/uart/0","w"),NULL};
    configASSERT(reply[0]);
#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
    int native_fd=open("/dev/secondary",O_RDWR|O_NONBLOCK);
    configASSERT(native_fd>=0);
    reply[1]=fdopen(native_fd,"w");configASSERT(reply[1]);ports=2;
#endif
    serial_frame frames[2];
    for (int i=0;i<ports;i++) {
        char *buffer=malloc(MAX_BODY+1);configASSERT(buffer);
        serial_frame_init(&frames[i],buffer,MAX_BODY);
        setvbuf(reply[i],NULL,_IONBF,0);
    }
    printf("USB_SETUP transports=%s\n",ports==2?"uart0,native-usb":"uart0");
    for (;;) {
        ota_heartbeat(2);ota_watchdog_fault_checkpoint(2);
        /* Bounded fair polling: neither a UART flood nor a partial USB frame
         * can starve the other transport or the task-progress heartbeat. */
        for (int port=0;port<ports;port++) for (unsigned n=0;n<256;n++) {
        unsigned char ch;
        int count=port==0?uart_read_bytes(UART_NUM_0,&ch,1,0):native_setup_read(&ch);
        if (count!=1) break;
        serial_frame *frame=&frames[port];
        if (!serial_frame_feed(frame,ch)) continue;
        cJSON *req=frame->overflow?NULL:parse(frame->data), *out;
        int status=200;
        xSemaphoreTake(lock,portMAX_DELAY);
        const char *op=text(req,"op");
        if (op && !strcmp(op,"provision") && (ota_upload_in_progress() || wifi_ap_trial_pending())) {
            status=503;out=message("OTA reservation active; no credentials changed",false);
        } else if (op && !strcmp(op,"provision")) {
            bool ok=provision(req);
            out=message(ok?"Credentials saved; connecting":"Invalid credentials or provisioning failure",ok);
            if (!ok) status=400;
        } else if (op && (!strcmp(op,"io_arm") || !strcmp(op,"io_disarm"))) {
            out=usb_io_mode(req,!strcmp(op,"io_arm"),&status);
        } else if (op && !strcmp(op,"request")) {
            const char *method=text(req,"method"),*path=text(req,"path"),*body=text(req,"body");
            if (method && path) out=dispatch(method,path,body?body:"",&status);
            else { out=message("method and path required",false); status=400; }
        } else { out=message("Invalid USB request",false); status=400; }
        cJSON *envelope=cJSON_CreateObject();
        cJSON_AddNumberToObject(envelope,"status",status);
        cJSON *id=cJSON_GetObjectItemCaseSensitive(req,"id");
        if (cJSON_IsNumber(id)) cJSON_AddNumberToObject(envelope,"id",id->valuedouble);
        cJSON_AddItemToObject(envelope,"data",out);
        char *s=cJSON_PrintUnformatted(envelope);
        if (s) {
            /* Reply ONLY to its source transport: simultaneous clients may use
             * identical IDs. Serialize with stdout logs to avoid torn frames,
             * but do not broadcast acks to the other port's client. */
            flockfile(stdout);
            fprintf(reply[port],"USB_RESPONSE %s\n",s);
            funlockfile(stdout);
            free(s);
        }
        cJSON_Delete(envelope);
        xSemaphoreGive(lock);
        /* Never echo USB input: it can contain a Wi-Fi password. */
        if (req) {
            cJSON *password=cJSON_GetObjectItemCaseSensitive(req,"password");
            if (cJSON_IsString(password)) memset(password->valuestring,0,strlen(password->valuestring));
        }
        cJSON_Delete(req); serial_frame_reset(frame);
        }
        vTaskDelay(pdMS_TO_TICKS(10)+1);
    }
}
static void automation_task(void *arg)
{
    (void)arg;
    for (;;) {
        ota_heartbeat(0);ota_watchdog_fault_checkpoint(0);
        xSemaphoreTake(lock,portMAX_DELAY);
        if (use_network_clock) {
            engine_clock clock={.monotonic_ms=esp_timer_get_time()/1000};
            clock.valid=clock_service_sample(&clock.unix_seconds,&clock.local_seconds);
            engine_prepare_clock(&runtime_clock,&clock,&simulated_inputs);
        }
        if (outputs.active) {
            simulated_inputs.switch_state=outputs.switches[0];simulated_inputs.reset_switch=outputs.switches[1];
        }
        engine_tick(relays,&simulated_inputs,runtime_write,NULL,&automation_stats);
        engine_advance_inputs(&simulated_inputs);
        xSemaphoreGive(lock);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
static void input_task(void *arg)
{
    (void)arg;
    for (;;) {
        ota_heartbeat(3);ota_watchdog_fault_checkpoint(3);
        xSemaphoreTake(lock,portMAX_DELAY);
        io_backend_sample(&outputs,(uint32_t)(esp_timer_get_time()/1000));
        xSemaphoreGive(lock);vTaskDelay(pdMS_TO_TICKS(10)+1);
    }
}
void runtime_start(void)
{
    const char *contract=io_gpio_operations()?"relay-profile1":"native-profile1";
    ESP_ERROR_CHECK(!strcmp(esp_app_get_description()->version,contract)?ESP_OK:ESP_ERR_INVALID_VERSION);
    uint8_t mac[6];ESP_ERROR_CHECK(esp_efuse_mac_get_default(mac));
    for (unsigned i=0;i<6;i++) snprintf(device_id+2*i,3,"%02x",mac[i]);
    /* Do not silently erase NVS on schema/storage failure. */
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(nvs_open("bench",NVS_READWRITE,&store));
    uint32_t schema=1;
    esp_err_t schema_err=nvs_get_u32(store,"schema",&schema);
    if (schema_err!=ESP_OK && schema_err!=ESP_ERR_NVS_NOT_FOUND) ESP_ERROR_CHECK(schema_err);
    /* Refuse an unknown schema instead of destroying newer configuration. */
    ESP_ERROR_CHECK(schema==1 ? ESP_OK : ESP_ERR_INVALID_VERSION);
    ESP_ERROR_CHECK(nvs_set_u32(store,"schema",1));
    ESP_ERROR_CHECK(nvs_commit(store));
    lock=xSemaphoreCreateMutex(); configASSERT(lock);
    load_relays(); configASSERT(relays);
    simulated_inputs=rule_inputs_default();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    netif=esp_netif_create_default_wifi_sta(); configASSERT(netif);
    clock_service_init();load_profile();
    ESP_ERROR_CHECK(engine_apply_commands(relays,engine_mock_write,&mock_outputs));
    ESP_ERROR_CHECK(io_layout_hash(device_profile,boot_layout)?ESP_OK:ESP_ERR_INVALID_STATE);
    if (io_gpio_operations()) {
        char record[80]={0};size_t length=sizeof(record);
        esp_err_t armed=nvs_get_str(store,"arm_v1",record,&length);
        if (armed!=ESP_OK && armed!=ESP_ERR_NVS_NOT_FOUND) ESP_ERROR_CHECK(armed);
        if (armed==ESP_OK && io_arm_record_matches(record,device_id,boot_layout) && physical_ready(device_profile)) {
            ESP_ERROR_CHECK(wifi_ap_trial_enabled()?ESP_ERR_INVALID_STATE:ESP_OK);
            snprintf(armed_layout,sizeof(armed_layout),"%s",boot_layout);
            ESP_ERROR_CHECK(io_backend_start(&outputs,device_profile,io_gpio_operations(),&gpio_driver,(uint32_t)(esp_timer_get_time()/1000)));
            io_backend_baseline(&outputs,&simulated_inputs);
        }
    }
    ESP_ERROR_CHECK(esp_netif_set_hostname(netif,hostname));
    wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(wifi_apply_power_policy());
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,ESP_EVENT_ANY_ID,wifi_event,NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT,IP_EVENT_STA_GOT_IP,wifi_event,NULL));
    ESP_ERROR_CHECK(mdns_init());
    ESP_ERROR_CHECK(mdns_hostname_set(hostname));
    ESP_ERROR_CHECK(mdns_service_add(NULL,"_http","_tcp",80,NULL,0));
    httpd_config_t http=HTTPD_DEFAULT_CONFIG();
    http.stack_size=8192; http.max_open_sockets=4;
    http.lru_purge_enable=true; http.recv_wait_timeout=3;
    http.uri_match_fn=httpd_uri_match_wildcard;
    httpd_handle_t server;
    ESP_ERROR_CHECK(httpd_start(&server,&http));
    ota_register(server); /* exact binary route must precede wildcard routes */
    httpd_uri_t get={.uri="/api/*",.method=HTTP_GET,.handler=http_api};
    httpd_uri_t post={.uri="/api/*",.method=HTTP_POST,.handler=http_api};
    ESP_ERROR_CHECK(httpd_register_uri_handler(server,&get));
    ESP_ERROR_CHECK(httpd_register_uri_handler(server,&post));
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0,16384,0,0,NULL,0));
    configASSERT(xTaskCreate(serial_task,"usb_setup",8192,NULL,3,NULL)==pdPASS);
    configASSERT(xTaskCreate(automation_task,"rules",16384,NULL,2,NULL)==pdPASS);
    configASSERT(xTaskCreate(network_task,"wifi_retry",4096,NULL,2,NULL)==pdPASS);
    configASSERT(xTaskCreate(input_task,"inputs",4096,NULL,3,NULL)==pdPASS);
    wifi_config_t cfg={0}; size_t size=sizeof(cfg);
    if (nvs_get_blob(store,"wifi",&cfg,&size)==ESP_OK && size==sizeof(cfg)) {
        ESP_ERROR_CHECK(wifi_ap_trial_prepare(&cfg,(uint32_t)(esp_timer_get_time()/1000)));
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA,&cfg));
        atomic_store(&wifi_enabled,true);
        ESP_ERROR_CHECK(esp_wifi_start());
    }
    memset(&cfg,0,sizeof(cfg));
    /* Always-on maintenance summary, deliberately omitting credentials, SSID,
       addresses, chip IDs, relay labels and consistency/arming tokens. */
    printf("RUNTIME_STATE contract=%s relays=%d gpio_active=%d clock_source=%s timezone_confirmed=%d\n",
           contract,cJSON_GetArraySize(relays),outputs.active,
           use_network_clock?"network":"manual",text(device_profile,"timezone")!=NULL);
    printf("RUNTIME_READY hostname=%s simulated=%s wifi_provisioned=%d\n",active_hostname,outputs.active?"false":"true",atomic_load(&wifi_enabled));
}
