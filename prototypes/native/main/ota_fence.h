#pragma once
#include <stdbool.h>
bool ota_fence_hash(const char *device,const char *boot,const char *layout,const char *revision,const char *elf,bool active,bool armed,char out[65]);
bool ota_fence_accept(bool controller,const char *expected,const char *current);
bool ota_fence_selftests(void);
