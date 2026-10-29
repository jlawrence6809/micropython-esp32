#pragma once
#include <stdint.h>
#include <stdbool.h>
#define RUNTIME_TASKS 4
#define RUNTIME_LEASE_MS 10000u
/* Pure progress monitor; unsigned subtraction handles millis/counter rollover. */
typedef struct {
    unsigned observed[RUNTIME_TASKS];
    uint32_t changed_at[RUNTIME_TASKS];
} runtime_lease;
void runtime_lease_init(runtime_lease *,const unsigned counts[RUNTIME_TASKS],uint32_t now);
unsigned runtime_lease_poll(runtime_lease *,const unsigned counts[RUNTIME_TASKS],uint32_t now);
bool runtime_lease_selftests(void);
