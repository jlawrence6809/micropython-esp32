#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "cJSON.h"
void clock_service_init(void);
bool clock_service_sample(int64_t *unix_seconds, int *local_seconds);
void clock_service_network_ready(void);
cJSON *clock_service_status(void);
cJSON *clock_service_zones(void);
cJSON *clock_service_view_at(long long unix_seconds);
bool clock_service_zone_supported(const char *name);
bool clock_service_use_zone(const char *name);
