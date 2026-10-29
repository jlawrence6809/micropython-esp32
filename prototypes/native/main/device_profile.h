#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "cJSON.h"
bool profile_valid_relays(cJSON *array);
/* Returns an owned canonical copy; never configures GPIO or writes storage. */
cJSON *profile_normalize(cJSON *profile);
cJSON *profile_from_legacy(cJSON *relays, const char *timezone);
/* Revision excludes runtime values/diagnostics; generation tracks explicit commits. */
bool profile_edit_revision(cJSON *profile,uint32_t generation,char hash[65]);
cJSON *profile_edit_merge(cJSON *current,cJSON *changes);
bool profile_edit_selftests(void);
