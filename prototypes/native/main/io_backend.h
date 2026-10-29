#pragma once
#include "relay_engine.h"
#include "board_io.h"

typedef struct {
    esp_err_t (*relay_open)(void *,unsigned,int,bool,bool);
    esp_err_t (*relay_set)(void *,unsigned,bool);
    esp_err_t (*relay_close)(void *,unsigned);
    esp_err_t (*switch_open)(void *,unsigned,int,uint32_t);
    bool (*switch_sample)(void *,unsigned,uint32_t);
    esp_err_t (*switch_close)(void *,unsigned);
    esp_err_t (*relay_configure)(void *,unsigned,bool,bool);
} io_operations;
typedef struct {
    bool active, cleanup_failed;
    unsigned count;
    int pins[16], switch_pins[2], failure_pin;
    bool inverted[16], commands[16], attempted[16], switch_attempted[2], switches[2];
    const io_operations *ops;
    void *driver;
} io_backend;
typedef struct {relay_gpio relays[16];switch_gpio switches[2];} io_gpio_driver;

bool io_layout_hash(cJSON *profile,char hash[65]);
bool io_live_settings_compatible(cJSON *current,cJSON *next);
/* Only switch pin changes, all relays manual/current/default OFF, no straps. */
bool io_live_switch_settings_compatible(cJSON *current,cJSON *next);
esp_err_t io_backend_reconfigure_switches(io_backend *,cJSON *next,uint32_t now);
void io_backend_baseline_switches(io_backend *,rule_inputs *);
bool io_arm_record_matches(const char *record,const char *device_id,const char *layout_hash);
esp_err_t io_backend_start(io_backend *,cJSON *profile,const io_operations *,void *driver,uint32_t now);
esp_err_t io_backend_stop(io_backend *);
esp_err_t io_backend_write(void *,int pin,bool command,bool inverted);
void io_backend_sample(io_backend *,uint32_t now);
void io_backend_baseline(io_backend *,rule_inputs *);
void io_backend_publish(io_backend *,cJSON *relays);
bool io_backend_apply(io_backend *,cJSON *relays);
/* Real operations do not exist in a normal bench binary. */
const io_operations *io_gpio_operations(void);
bool io_backend_selftests(void);
