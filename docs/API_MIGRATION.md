# API Migration Guide

This document maps the original C/ESP-IDF API endpoints to the new MicroPython implementation.

## System Endpoints

| Original Endpoint | Method | New Endpoint          | Implementation Status | Notes                                 |
| :---------------- | :----- | :-------------------- | :-------------------- | :------------------------------------ |
| `/global-info`    | GET    | `/api/status`         | ✅ Implemented        | Returns memory, uptime, platform info |
| `/reset`          | POST   | `/api/restart`        | ✅ Implemented        | Restarts the ESP32                    |
| `/storage-info`   | GET    | `/api/storage`        | ⏳ Pending            | Returns filesystem usage              |
| `/gpio-options`   | GET    | `/api/gpio/available` | ⏳ Pending            | Returns list of safe-to-use GPIO pins |

## Hardware Control

| Original Endpoint | Method | New Endpoint          | Implementation Status | Notes                                               |
| :---------------- | :----- | :-------------------- | :-------------------- | :-------------------------------------------------- |
| `/relay-control`  | POST   | `/api/relays/control` | ⏳ Pending            | Control relay state `{label: "Light", state: true}` |
| `/relay-config`   | GET    | `/api/relays/config`  | ⏳ Pending            | Get list of configured relays                       |
| `/relay-config`   | POST   | `/api/relays/config`  | ⏳ Pending            | Update relay configuration (pins, labels, rules)    |
| `/sensor-info`    | GET    | `/api/sensors`        | ⏳ Pending            | Get current sensor readings (Temp, Light, Humidity) |

## WiFi Management

| Original Endpoint | Method | New Endpoint        | Implementation Status | Notes                                                   |
| :---------------- | :----- | :------------------ | :-------------------- | :------------------------------------------------------ |
| `/wifi-status`    | GET    | `/api/wifi/status`  | ⏳ Pending            | IP, RSSI, SSID, Connection State                        |
| `/wifi-connect`   | POST   | `/api/wifi/connect` | ⏳ Pending            | Connect to new network `{ssid: "...", password: "..."}` |
| `/wifi-settings`  | POST   | `/api/wifi/connect` | ⏳ Pending            | Same as connect (consolidated)                          |

## Automation

| Original Endpoint | Method | New Endpoint | Implementation Status | Notes                                                |
| :---------------- | :----- | :----------- | :-------------------- | :--------------------------------------------------- |
| `/validate-rule`  | POST   | N/A          | ❌ Removed            | Rules are now Python code, not JSON DSL              |
| N/A               | POST   | `/api/save`  | ✅ Implemented        | Save arbitrary Python code (e.g. automation scripts) |

## Data Formats

### Relay Config Object

```json
{
  "relays": [
    {
      "pin": 21,
      "label": "Grow Light",
      "isInverted": false,
      "currentValue": 0,
      "defaultValue": 0,
      "enabled": true
    }
  ]
}
```

### Sensor Data Object

```json
{
  "temperature": 24.5,
  "humidity": 60.2,
  "light": 450,
  "switch": true
}
```
