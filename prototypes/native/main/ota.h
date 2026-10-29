#pragma once
#include <stdbool.h>
#include "esp_http_server.h"
#include "cJSON.h"
void ota_register(httpd_handle_t server);
bool ota_upload_in_progress(void);
cJSON *ota_status(void);
void ota_boot_check(bool selftests_passed);
void ota_health_start(void);
void ota_heartbeat(unsigned task);
void ota_watchdog_fault_checkpoint(unsigned task);
cJSON *ota_watchdog_status(void);
