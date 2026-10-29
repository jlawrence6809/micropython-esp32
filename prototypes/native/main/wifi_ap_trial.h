#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_wifi.h"
bool wifi_ap_trial_enabled(void);
bool wifi_ap_trial_pending(void);
esp_err_t wifi_ap_trial_prepare(wifi_config_t *config, uint32_t now_ms);
esp_err_t wifi_ap_trial_poll(uint32_t now_ms);
