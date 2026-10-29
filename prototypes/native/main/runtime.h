#pragma once
#include <stddef.h>
#include <stdbool.h>
typedef struct {
    double temperature, last_temperature, humidity, last_humidity, light, last_light;
    bool switch_state, last_switch_state, reset_switch, last_reset_switch;
    /* -1 means invalid/uninitialized clock. Seconds since local midnight. */
    int time_seconds, last_time_seconds;
} rule_inputs;
rule_inputs rule_inputs_default(void);
int evaluate_inputs(const char *source, const rule_inputs *inputs, char *error, size_t error_size, size_t *peak);
int evaluate(const char *source, double temperature, char *error, size_t error_size, size_t *peak);
void runtime_start(void);
/* Caller has claimed ota upload reservation; takes runtime lock only briefly. */
bool runtime_ota_reserve(const char *expected_fence);
