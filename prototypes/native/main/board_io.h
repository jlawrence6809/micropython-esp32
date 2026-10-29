#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "driver/i2c_master.h"
#include "cJSON.h"

typedef struct { int pin; bool inverted, opened, command; } relay_gpio;
bool io_pin_allowed(int pin);
int relay_gpio_level(bool command, bool inverted);
esp_err_t relay_gpio_open(relay_gpio *relay, int pin, bool inverted, bool boot_value);
esp_err_t relay_gpio_set(relay_gpio *relay, bool command);
esp_err_t relay_gpio_configure(relay_gpio *relay, bool inverted, bool command);
esp_err_t relay_gpio_close(relay_gpio *relay);

typedef struct {
    bool stable, candidate;
    uint32_t candidate_since, interval_ms;
} switch_debounce;
void switch_debounce_init(switch_debounce *d, bool initial, uint32_t now, uint32_t interval);
bool switch_debounce_update(switch_debounce *d, bool raw_pressed, uint32_t now);

typedef struct {
    int pin; bool opened;
    switch_debounce debounce;
} switch_gpio;
esp_err_t switch_gpio_open(switch_gpio *s, int pin, uint32_t now);
bool switch_gpio_sample(switch_gpio *s, uint32_t now);
esp_err_t switch_gpio_close(switch_gpio *s);

typedef struct {
    i2c_master_bus_handle_t bus;
    i2c_master_dev_handle_t device;
    uint32_t started_at;
    bool pending;
} aht21_sensor;
uint8_t aht21_crc(const uint8_t *data, unsigned length);
esp_err_t aht21_decode(const uint8_t frame[7], double *temperature, double *humidity);
esp_err_t aht21_open(aht21_sensor *sensor, int scl, int sda);
esp_err_t aht21_start(aht21_sensor *sensor, uint32_t now);
esp_err_t aht21_poll(aht21_sensor *sensor, uint32_t now, double *temperature, double *humidity);
esp_err_t aht21_close(aht21_sensor *sensor);
bool board_io_selftests(void);
cJSON *board_io_status(void);
cJSON *board_io_plan(cJSON *relays, cJSON *sensor_pins);
