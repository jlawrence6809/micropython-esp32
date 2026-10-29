/* Compile-time board policy. No SDK calls, storage or GPIO activation.
 * Host C tests retain the historical S3 policy unless ESP32 is selected.
 * Deliberately do not widen the S3 allowlist when enabling original ESP32.
 */
#pragma once
#ifdef ESP_PLATFORM
#include "sdkconfig.h"
#endif
#if defined(CONFIG_IDF_TARGET_ESP32)
#define GARDEN_TARGET_NAME "esp32"
#define GARDEN_IMAGE_CHIP_ID 0
/* UART0 (1/3), SPI flash (6..11), input-only (34..39), boot0/2 excluded.
 * 12 is necessary for Relay_X8 K7; 5/12/15 are strapping pins: external
 * reset-time bias must be verified, independently of application defaults.
 */
#define GARDEN_ALLOWED_PINS {4,5,12,13,14,15,16,17,18,19,21,22,23,25,26,27,32,33}
#define GARDEN_TEST_SECOND_RELAY_PIN 18
#define GARDEN_FACTORY_RELAY_PIN 4
#elif defined(CONFIG_IDF_TARGET_ESP32S3) || !defined(ESP_PLATFORM)
#define GARDEN_TARGET_NAME "esp32s3"
#define GARDEN_IMAGE_CHIP_ID 9
#define GARDEN_ALLOWED_PINS {1,2,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,21,38,39,40,41,42,47,48}
#define GARDEN_TEST_SECOND_RELAY_PIN 6
#define GARDEN_FACTORY_RELAY_PIN 1
#else
#error "Garden supports only original ESP32 and ESP32-S3"
#endif
