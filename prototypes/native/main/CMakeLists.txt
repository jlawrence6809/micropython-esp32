idf_component_register(SRCS "main.c" "runtime.c" "serial_frame.c" "wifi_trace.c" "wifi_ap_trial.c" "rules.c" "ota.c" "ota_fence.c" "clock_service.c" "board_io.c" "relay_engine.c" "device_profile.c" "profile_edit.c" "io_backend.c" "runtime_lease.c" INCLUDE_DIRS "."
    REQUIRES lua esp_timer app_update nvs_flash esp_wifi esp_event esp_netif
    esp_http_server json esp_driver_uart mdns mbedtls lwip esp_driver_gpio esp_driver_i2c)
