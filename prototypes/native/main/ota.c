/* Unauthenticated LAN-only OTA. Image/digest checks are NOT authentication. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdatomic.h>
#include "ota.h"
#include "target_board.h"
#include "runtime.h"
#include "runtime_lease.h"
#include "esp_attr.h"
#include "esp_app_format.h"
#include "esp_app_desc.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mbedtls/sha256.h"

static atomic_bool uploading, streaming, healthy;
static char boot_id[17];
bool ota_upload_in_progress(void) { return atomic_load(&uploading); }
_Static_assert(RUNTIME_TASKS==4,"Update task names and RTC mask validation when adding tasks");
static atomic_uint beats[RUNTIME_TASKS]; /* automation, network, USB, input sampler */
static atomic_bool watchdog_active;
static atomic_uint ages[RUNTIME_TASKS], timeout_mask;
static unsigned previous_watchdog_mask;
/* Volatile RTC diagnostic only, never flash/config. A reset can erase it. */
static RTC_NOINIT_ATTR volatile struct {uint32_t magic,mask,inverse;} watchdog_reset;
#define WATCHDOG_RESET_MAGIC 0x47445744u

static const char *state_name(const esp_partition_t *p)
{
    esp_ota_img_states_t state;
    if (!p || esp_ota_get_state_partition(p,&state)!=ESP_OK) return "undefined";
    switch (state) {
        case ESP_OTA_IMG_NEW:return "new";
        case ESP_OTA_IMG_PENDING_VERIFY:return "pending";
        case ESP_OTA_IMG_VALID:return "valid";
        case ESP_OTA_IMG_INVALID:return "invalid";
        case ESP_OTA_IMG_ABORTED:return "aborted";
        default:return "undefined";
    }
}
cJSON *ota_status(void)
{
    cJSON *o=cJSON_CreateObject();
    const esp_partition_t *running=esp_ota_get_running_partition();
    const esp_partition_t *boot=esp_ota_get_boot_partition();
    const esp_partition_t *next=esp_ota_get_next_update_partition(NULL);
    /* esp_app_get_elf_sha256() may expose only the configured logging prefix.
       Format the complete descriptor digest for unambiguous update verification. */
    char sha[65];
    const uint8_t *digest=esp_app_get_description()->app_elf_sha256;
    for (unsigned i=0;i<32;i++) snprintf(sha+2*i,3,"%02x",digest[i]);
    cJSON_AddStringToObject(o,"running_slot",running?running->label:"");
    cJSON_AddStringToObject(o,"boot_slot",boot?boot->label:"");
    cJSON_AddStringToObject(o,"update_slot",next?next->label:"");
    cJSON_AddStringToObject(o,"running_state",state_name(running));
    cJSON_AddStringToObject(o,"update_state",state_name(next));
    cJSON_AddStringToObject(o,"elf_sha256",sha);
    cJSON_AddStringToObject(o,"version",esp_app_get_description()->version);
    cJSON_AddStringToObject(o,"chip_target",GARDEN_TARGET_NAME);
    cJSON_AddNumberToObject(o,"image_chip_id",GARDEN_IMAGE_CHIP_ID);
    cJSON_AddNumberToObject(o,"update_partition_bytes",next?next->size:0);
    cJSON_AddStringToObject(o,"boot_id",boot_id);
    cJSON_AddBoolToObject(o,"healthy",atomic_load(&healthy));
    cJSON_AddBoolToObject(o,"uploading",atomic_load(&uploading));
    cJSON_AddBoolToObject(o,"image_streaming",atomic_load(&streaming));
    cJSON_AddBoolToObject(o,"runtime_watchdog_active",atomic_load(&watchdog_active));
    cJSON_AddNumberToObject(o,"previous_watchdog_mask",previous_watchdog_mask);
    return o;
}
void ota_heartbeat(unsigned task)
{
    if (task<RUNTIME_TASKS) atomic_fetch_add(&beats[task],1);
}
cJSON *ota_watchdog_status(void)
{
    cJSON *o=cJSON_CreateObject(),*tasks=cJSON_CreateObject();
    cJSON_AddBoolToObject(o,"monitor_active",atomic_load(&watchdog_active));
    cJSON_AddNumberToObject(o,"lease_ms",RUNTIME_LEASE_MS);
    cJSON_AddNumberToObject(o,"previous_watchdog_mask",previous_watchdog_mask);
    cJSON_AddNumberToObject(o,"timeout_mask",atomic_load(&timeout_mask));
    const char *names[]={"rules","network","usb","inputs"};
    for (unsigned i=0;i<RUNTIME_TASKS;i++) cJSON_AddNumberToObject(tasks,names[i],atomic_load(&ages[i]));
    cJSON_AddItemToObject(o,"observed_progress_age_ms",tasks);
#ifdef CONFIG_BENCH_WATCHDOG_STALL
    cJSON_AddBoolToObject(o,"fault_injection",true);
    cJSON_AddNumberToObject(o,"fault_task",CONFIG_BENCH_WATCHDOG_STALL_TASK);
#else
    cJSON_AddBoolToObject(o,"fault_injection",false);
    cJSON_AddNumberToObject(o,"fault_task",-1);
#endif
    return o;
}
void ota_watchdog_fault_checkpoint(unsigned task)
{
#ifdef CONFIG_BENCH_WATCHDOG_STALL
    if (task==CONFIG_BENCH_WATCHDOG_STALL_TASK && atomic_load(&healthy)) {
        printf("BENCH_RUNTIME_STALL task=%u\n",task);
        for (;;) vTaskDelay(pdMS_TO_TICKS(1000)); /* no lock held, no heartbeat */
    }
#else
    (void)task;
#endif
}
static void restart_task(void *arg)
{
    (void)arg;ulTaskNotifyTake(pdTRUE,portMAX_DELAY);
    vTaskDelay(pdMS_TO_TICKS(750));esp_restart();
}
static esp_err_t fail(httpd_req_t *req,const char *status,const char *message)
{
    httpd_resp_set_status(req,status);httpd_resp_set_type(req,"application/json");
    httpd_resp_set_hdr(req,"Connection","close");
    httpd_resp_sendstr(req,message);
    /* Avoid losing small rejection replies to TCP RST. This is a bounded discard,
       never an unbounded purge of a declared image. One blocking recv can extend
       the cooperative 250ms budget by the configured socket timeout. */
    char discard[512];size_t left=req->content_len<16384?req->content_len:16384;
    int64_t until=esp_timer_get_time()+250000;
    while (left && esp_timer_get_time()<until) {
        int n=httpd_req_recv(req,discard,left<sizeof(discard)?left:sizeof(discard));
        if (n<=0) break;
        left-=n;
    }
    return ESP_FAIL; /* Never interpret an unread/partial image as another request. */
}
static int hex(char c)
{
    if (c>='0' && c<='9') return c-'0';
    if (c>='a' && c<='f') return c-'a'+10;
    if (c>='A' && c<='F') return c-'A'+10;
    return -1;
}
static esp_err_t upload(httpd_req_t *req)
{
    const esp_partition_t *partition=esp_ota_get_next_update_partition(NULL);
    const size_t prefix_size=sizeof(esp_image_header_t)+sizeof(esp_image_segment_header_t)+sizeof(esp_app_desc_t);
    if (!partition || req->content_len<prefix_size || req->content_len>partition->size)
        return fail(req,"413 Payload Too Large","{\"error\":\"invalid image size\"}");
    char expected_hex[65];unsigned char expected[32];
    if (httpd_req_get_hdr_value_len(req,"X-Firmware-SHA256")!=64 ||
        httpd_req_get_hdr_value_str(req,"X-Firmware-SHA256",expected_hex,sizeof(expected_hex))!=ESP_OK)
        return fail(req,"400 Bad Request","{\"error\":\"SHA256 header required\"}");
    for (unsigned i=0;i<32;i++) {
        int a=hex(expected_hex[2*i]),b=hex(expected_hex[2*i+1]);
        if (a<0 || b<0) return fail(req,"400 Bad Request","{\"error\":\"invalid digest\"}");
        expected[i]=(a<<4)|b;
    }
    char fence[65];const char *expected_fence=NULL;
    size_t fence_length=httpd_req_get_hdr_value_len(req,"X-Garden-OTA-Fence");
    if (fence_length) {
        if (fence_length!=64 || httpd_req_get_hdr_value_str(req,"X-Garden-OTA-Fence",fence,sizeof(fence))!=ESP_OK)
            return fail(req,"400 Bad Request","{\"error\":\"invalid OTA fence header\"}");
        expected_fence=fence;
    }
    bool was_uploading=false;
    if (!atomic_compare_exchange_strong(&uploading,&was_uploading,true))
        return fail(req,"409 Conflict","{\"error\":\"update already in progress\"}");
    if (!runtime_ota_reserve(expected_fence)) {
        atomic_store(&uploading,false);
        return fail(req,"409 Conflict","{\"error\":\"OTA fence mismatch, pending maintenance state or unhealthy boot; controller fence required\"}");
    }
    unsigned char buffer[1024];size_t received=0;
    esp_ota_handle_t handle=0;bool begun=false;
    esp_err_t result=ESP_FAIL;
    int64_t deadline=esp_timer_get_time()+120000000;
    mbedtls_sha256_context hash;mbedtls_sha256_init(&hash);
    while (received<prefix_size) {
        int n=httpd_req_recv(req,(char *)buffer+received,prefix_size-received);
        if (n<=0 || esp_timer_get_time()>deadline) goto cleanup;
        received+=n;
    }
    esp_image_header_t header;esp_app_desc_t description;
    memcpy(&header,buffer,sizeof(header));
    memcpy(&description,buffer+sizeof(header)+sizeof(esp_image_segment_header_t),sizeof(description));
    if (header.magic!=ESP_IMAGE_HEADER_MAGIC || header.chip_id!=GARDEN_IMAGE_CHIP_ID ||
        description.magic_word!=ESP_APP_DESC_MAGIC_WORD ||
        memcmp(description.project_name,"garden_native_probe\0",20)!=0 ||
        memcmp(description.version,esp_app_get_description()->version,sizeof(description.version))!=0) goto cleanup;
    result=esp_ota_begin(partition,req->content_len,&handle);
    if (result!=ESP_OK) goto cleanup;
    begun=true;
    if (mbedtls_sha256_starts(&hash,0)!=0 || mbedtls_sha256_update(&hash,buffer,received)!=0) goto cleanup;
    result=esp_ota_write(handle,buffer,received);
    if (result!=ESP_OK) goto cleanup;
    atomic_store(&streaming,true);
    unsigned chunks=0;
    while (received<req->content_len) {
        size_t remaining=req->content_len-received;
        int n=httpd_req_recv(req,(char *)buffer,remaining>sizeof(buffer)?sizeof(buffer):remaining);
        if (n<=0 || esp_timer_get_time()>deadline) { result=ESP_FAIL;goto cleanup; }
        if (mbedtls_sha256_update(&hash,buffer,n)!=0) { result=ESP_FAIL;goto cleanup; }
        result=esp_ota_write(handle,buffer,n);
        if (result!=ESP_OK) goto cleanup;
        received+=n;
        if (++chunks%16==0) vTaskDelay(1);
    }
    atomic_store(&streaming,false);
    unsigned char actual[32];
    if (mbedtls_sha256_finish(&hash,actual)!=0 || memcmp(actual,expected,sizeof(actual))!=0) {
        result=ESP_ERR_INVALID_CRC;goto cleanup;
    }
    result=esp_ota_end(handle);begun=false; /* end frees the handle, including on failure */
    if (result!=ESP_OK) goto cleanup;
    /* Preflight restart scheduling BEFORE changing boot selection. This task
       waits for notification until selection is safely committed below. */
    TaskHandle_t reboot=NULL;
    if (xTaskCreate(restart_task,"ota_restart",2048,NULL,1,&reboot)!=pdPASS) {
        result=ESP_ERR_NO_MEM;goto cleanup;
    }
    result=esp_ota_set_boot_partition(partition);
    if (result!=ESP_OK) { vTaskDelete(reboot);goto cleanup; }
    mbedtls_sha256_free(&hash);
    httpd_resp_set_type(req,"application/json");
    esp_err_t sent=httpd_resp_sendstr(req,"{\"success\":true,\"message\":\"Image staged; rebooting for health validation\"}");
    xTaskNotifyGive(reboot);
    /* If response is lost, the update may still happen. Clients must inspect
       status rather than automatically re-uploading. */
    return sent;
cleanup:
    atomic_store(&streaming,false);
    if (begun) esp_ota_abort(handle);
    mbedtls_sha256_free(&hash);
    atomic_store(&uploading,false);
    return fail(req,"400 Bad Request","{\"error\":\"Upload rejected or interrupted; boot slot unchanged\"}");
}
void ota_register(httpd_handle_t server)
{
    httpd_uri_t uri={.uri="/api/ota/upload",.method=HTTP_POST,.handler=upload};
    ESP_ERROR_CHECK(httpd_register_uri_handler(server,&uri));
}
void ota_boot_check(bool selftests_passed)
{
    if (esp_reset_reason()==ESP_RST_SW && watchdog_reset.magic==WATCHDOG_RESET_MAGIC &&
        watchdog_reset.mask && !(watchdog_reset.mask&~15u) && watchdog_reset.inverse==~watchdog_reset.mask)
        previous_watchdog_mask=watchdog_reset.mask;
    watchdog_reset.magic=0; /* Consume once; never turn this into a boot-loop counter. */
    /* Diagnostic reboot identity, not a token or cryptographic credential. */
    snprintf(boot_id,sizeof(boot_id),"%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random());
    const esp_partition_t *p=esp_ota_get_running_partition();
    esp_ota_img_states_t state;
    bool pending=esp_ota_get_state_partition(p,&state)==ESP_OK && state==ESP_OTA_IMG_PENDING_VERIFY;
#ifdef CONFIG_BENCH_OTA_FAIL_PENDING_BOOT
    if (pending) { printf("BENCH_OTA_INJECT_REBOOT\n");esp_restart(); }
#endif
    if (!selftests_passed) {
        if (pending) esp_ota_mark_app_invalid_rollback_and_reboot();
        abort(); /* Do not run a firmware that failed its own boot tests. */
    }
}
static void monitor_runtime(void)
{
    unsigned counts[RUNTIME_TASKS];runtime_lease lease;
    for (unsigned i=0;i<RUNTIME_TASKS;i++) counts[i]=atomic_load(&beats[i]);
    runtime_lease_init(&lease,counts,(uint32_t)(esp_timer_get_time()/1000));
    atomic_store(&watchdog_active,true);
    atomic_store(&healthy,true);printf("OTA_BOOT_HEALTHY\n");
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        uint32_t now=(uint32_t)(esp_timer_get_time()/1000);
        for (unsigned i=0;i<RUNTIME_TASKS;i++) counts[i]=atomic_load(&beats[i]);
        unsigned expired=runtime_lease_poll(&lease,counts,now);
        for (unsigned i=0;i<RUNTIME_TASKS;i++) atomic_store(&ages[i],(uint32_t)(now-lease.changed_at[i]));
        if (expired) {
            atomic_store(&healthy,false);atomic_store(&timeout_mask,expired);
            watchdog_reset.mask=expired;watchdog_reset.inverse=~expired;watchdog_reset.magic=WATCHDOG_RESET_MAGIC;
            atomic_thread_fence(memory_order_seq_cst);
            printf("RUNTIME_WATCHDOG_RESET mask=%u\n",expired);
            /* Once valid, restart this image, never roll back across later config
               changes. Boot defaults/ROM electrical behavior require hardware tests. */
            esp_restart();
        }
    }
}
static void health_task(void *arg)
{
    (void)arg;
    unsigned initial[RUNTIME_TASKS];
    for (unsigned i=0;i<RUNTIME_TASKS;i++) initial[i]=atomic_load(&beats[i]);
    for (unsigned waited=0;waited<30;waited++) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        if (waited<4) continue;
        bool alive=atomic_load(&beats[0])-initial[0]>=5 &&
            atomic_load(&beats[1])-initial[1]>=3 && atomic_load(&beats[2])-initial[2]>=10 &&
            atomic_load(&beats[3])-initial[3]>=10;
        if (alive && esp_get_free_heap_size()>32768) {
            esp_ota_img_states_t state;
            const esp_partition_t *p=esp_ota_get_running_partition();
            if (esp_ota_get_state_partition(p,&state)==ESP_OK && state==ESP_OTA_IMG_PENDING_VERIFY)
                ESP_ERROR_CHECK(esp_ota_mark_app_valid_cancel_rollback());
            monitor_runtime(); /* Remains alive after initial OTA validation. */
        }
    }
    /* Failure to establish local runtime health never marks a pending image valid.
       Wi-Fi availability is intentionally not a boot-validation prerequisite. */
    esp_ota_img_states_t state;
    const esp_partition_t *p=esp_ota_get_running_partition();
    if (esp_ota_get_state_partition(p,&state)==ESP_OK && state==ESP_OTA_IMG_PENDING_VERIFY)
        esp_ota_mark_app_invalid_rollback_and_reboot();
    abort();
}
void ota_health_start(void)
{
    configASSERT(xTaskCreate(health_task,"runtime_health",4096,NULL,1,NULL)==pdPASS);
}
