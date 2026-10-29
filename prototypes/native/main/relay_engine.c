/* One control path for runtime and deterministic tests. A writer callback is the
   ONLY output seam; normal bench firmware always uses the memory-only backend. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "relay_engine.h"
#include "board_io.h"

static bool flag(cJSON *o,const char *key) {return cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(o,key));}
static void error(cJSON *r,const char *message)
{
    cJSON_DeleteItemFromObject(r,"last_error");
    if (message) cJSON_AddStringToObject(r,"last_error",message); else cJSON_AddNullToObject(r,"last_error");
}
void engine_prepare_clock(engine_time_guard *g,const engine_clock *clock,rule_inputs *inputs)
{
    if (!clock->valid && g->initialized && g->previous.valid) g->discontinuities++;
    inputs->time_seconds=clock->valid?clock->local_seconds:-1;
    inputs->last_time_seconds=-1;
    if (clock->valid && g->initialized && g->previous.valid) {
        int64_t utc_delta=clock->unix_seconds-g->previous.unix_seconds;
        int64_t mono_delta=clock->monotonic_ms-g->previous.monotonic_ms;
        int local_delta=(clock->local_seconds-g->previous.local_seconds+86400)%86400;
        /* A first valid clock, backwards time, a large correction/stall or DST/
           timezone discontinuity establishes a baseline, not a catch-up event.
           Midnight with normal UTC/monotonic progression remains continuous. */
        bool continuous=utc_delta>=0 && utc_delta<=5 && mono_delta>=0 && mono_delta<=5000 &&
            llabs(utc_delta*1000-mono_delta)<=2000 && local_delta==utc_delta;
        if (continuous) inputs->last_time_seconds=g->previous.local_seconds;
        else g->discontinuities++;
    }
    g->previous=*clock;g->initialized=true;
}
void engine_advance_inputs(rule_inputs *in)
{
    in->last_temperature=in->temperature;in->last_humidity=in->humidity;in->last_light=in->light;
    in->last_switch_state=in->switch_state;in->last_reset_switch=in->reset_switch;
    in->last_time_seconds=in->time_seconds;
}
esp_err_t engine_mock_write(void *context,int pin,bool command,bool inverted)
{
    engine_mock *mock=context;
    if (!mock || !io_pin_allowed(pin)) return ESP_ERR_INVALID_ARG;
    if (mock->fail_pin==pin) return ESP_FAIL;
    mock->levels[pin]=relay_gpio_level(command,inverted);mock->writes++;return ESP_OK;
}
esp_err_t engine_apply_commands(cJSON *relays,engine_writer writer,void *context)
{
    cJSON *r;
    cJSON_ArrayForEach(r,relays) {
        int pin=cJSON_GetObjectItemCaseSensitive(r,"pin")->valueint;
        esp_err_t err=writer(context,pin,flag(r,"value"),flag(r,"isInverted"));
        if (err!=ESP_OK) return err;
    }
    return ESP_OK;
}
void engine_tick(cJSON *relays,const rule_inputs *inputs,engine_writer writer,void *context,engine_stats *stats)
{
    cJSON *r;
    cJSON_ArrayForEach(r,relays) {
        if (!flag(r,"auto")) continue;
        cJSON *source=cJSON_GetObjectItemCaseSensitive(r,"rule");
        if (!cJSON_IsString(source) || !source->valuestring[0]) continue;
        char failure[160]="";size_t peak;
        int result=evaluate_inputs(source->valuestring,inputs,failure,sizeof(failure),&peak);
        stats->evaluations++;
        if (result==-2) {error(r,failure);stats->errors++;continue;}
        if ((result==0 || result==1) && (result==1)!=flag(r,"value")) {
            int pin=cJSON_GetObjectItemCaseSensitive(r,"pin")->valueint;
            esp_err_t err=writer(context,pin,result==1,flag(r,"isInverted"));
            if (err!=ESP_OK) {
                snprintf(failure,sizeof(failure),"Output write failed: %s",esp_err_to_name(err));
                error(r,failure);stats->errors++;continue; /* Preserve published value. */
            }
            cJSON *value=cJSON_GetObjectItemCaseSensitive(r,"value");
            cJSON_SetBoolValue(value,result==1);stats->writes++;
        }
        error(r,NULL);
    }
}
