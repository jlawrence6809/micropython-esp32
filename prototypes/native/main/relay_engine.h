#pragma once
#include <stdint.h>
#include "runtime.h"
#include "cJSON.h"
#include "esp_err.h"

typedef struct { bool valid; int64_t unix_seconds, monotonic_ms; int local_seconds; } engine_clock;
typedef struct { engine_clock previous; bool initialized; unsigned discontinuities; } engine_time_guard;
typedef esp_err_t (*engine_writer)(void *context, int pin, bool command, bool inverted);
typedef struct { unsigned evaluations, writes, errors; } engine_stats;
typedef struct { bool levels[49]; int fail_pin; unsigned writes; } engine_mock;
void engine_prepare_clock(engine_time_guard *guard, const engine_clock *clock, rule_inputs *inputs);
void engine_advance_inputs(rule_inputs *inputs);
void engine_tick(cJSON *relays, const rule_inputs *inputs, engine_writer writer, void *context, engine_stats *stats);
esp_err_t engine_mock_write(void *context, int pin, bool command, bool inverted);
/* Synchronize explicit manual commands without running automation rules. */
esp_err_t engine_apply_commands(cJSON *relays, engine_writer writer, void *context);
