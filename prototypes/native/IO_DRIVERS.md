# GPIO, switches and AHT21 bench layer

Verified 2026-10-14 on the authorized disconnected ESP32-S3 spare. Neither live
controller was accessed or changed in this milestone. The normal firmware still
runs simulated relay/sensor APIs; the HAL is **not** yet wired into that runtime.

## Implemented HAL

### Relays

- Validated ESP32-S3 pin allowlist, excluding USB/UART, strapping and flash/PSRAM
  pins from the existing board definition.
- Logical on/off converted to electrical level with inversion respected.
- Preload configured default output level before enabling output at application
  initialization. Both default-on/default-off are supported.
- Command state updates only after a successful GPIO write.
- Explicit cleanup disables output and releases pulls; errors are surfaced and
  contexts retained on cleanup failure rather than pretending resources vanished.

This does not guarantee safe voltages before application initialization, during
ROM/reset/brownout or on actual relay modules. External biasing, module polarity
and power/reset behavior still need physical verification. No relay contacts,
loads, oscilloscope or meter were connected for these tests.

### Switches

- Active-low inputs with pull-up, matching the current MicroPython implementation.
- 40 ms stable-candidate debounce, based on monotonic unsigned millisecond deltas;
  wrap-around, bounce, hold and release tested.
- Initialize from sampled input rather than assuming false and synthesizing a
  startup edge. Electrical startup/bounce behavior on actual wiring remains untested.

### AHT21

- Native I2C, address 0x38, 100 kHz; complete SDA/SCL pair required.
- Probe before use; bounded SDK timeout per I2C transaction (20 ms).
- Calibration check/initialization and start/poll measurement API.
- Wait at least 80 ms before reading; busy measurements stop after a 200 ms
  sampling deadline (plus any in-progress bounded I2C transaction/scheduling).
- Validate busy/calibration bits and CRC-8 before publishing temperature/humidity.
- Decode both values from one frame, using 20-bit scaling; invalid frames return
  missing values, not stale valid-looking measurements.
- Explicit device/bus cleanup; no infinite sensor-busy loop.

Only codec fixtures and the missing-device hardware path have been verified.
An actual AHT21 is not connected, so successful measurement/calibration, accuracy,
external pull-ups, disconnected/stuck-bus recovery and long-running sensor behavior
are NOT verified. This driver is not yet used by the normal sensor API, which
continues to label its values simulated.

DS18B20 and ADC/photo-sensor drivers are not implemented. Both are disabled in the
captured live profiles. Plans requesting those features explicitly fail rather
than silently pretending they work.

## Pure configuration planning

`POST /api/bench/io-plan` accepts `{relays, sensor_pins}`. It checks:

- Allowed/unique output pins and required inversion/default booleans.
- All six sensor-pin fields, with -1 meaning disabled.
- No output/input/I2C pin collisions, no duplicate I2C pins, complete I2C pair.
- No unsupported enabled optional sensors.

The response describes application-start relay levels and switch/I2C properties.
It never configures hardware, changes settings or persists the proposed profile.
Both private controller profiles passed: all 17 declared boot levels matched their
recorded default values and inversion. This verifies the plan, not actual wiring.
Eight deliberate invalid-plan cases were rejected without modifying relay config.

`GET /api/bench/io-status` reports software test results, whether physical tests
ran on this boot, pin-release verification and `runtime_drives_gpio: false`.

## Test coverage

Every normal boot runs **13 pure I/O tests**, in addition to the 14 Lua boot tests:
relay level matrix, reserved-pin rejection, switch bounce/hold/release/wrap/startup,
known sensor frame, independent CRC reference vector, corrupt CRC, busy and
uncalibrated frames.

A separate build with `CONFIG_BENCH_IO_SELFTEST=y` adds four grouped hardware tests:

1. GPIO4 active-high driver: both initial defaults and subsequent commands, with
   actual pad-level readback.
2. GPIO4 active-low driver: the same default/command matrix with inversion.
3. GPIO5 active-low input, using internal pull-up/down to exercise sample/debounce.
4. Missing AHT21 on SCL1/SDA2 returns promptly and releases bus resources.

GPIO4/5 cleanup was checked through `gpio_get_io_config`: output disabled, input
allowed, pulls disabled. The last missing-sensor probe took **882 microseconds**.
All **17 I/O cases** passed on the diagnostic image. No configured RGB LED pin
(GPIO48 in the board definition) was exercised by this test, and no LED-animation
code is enabled. The diagnostic only touches GPIO4/5 and I2C on GPIO1/2.

The normal image was restored and verified afterward: 13 software cases pass,
physical selftest flag is disabled, and generic API remains simulation-only.
USB regression, 85 private rule comparisons, both profile persistence/defaults,
HTTP checks and pin plans passed. A 200-rule-validation sample had unchanged free
heap, 203,952 -> 203,952 bytes; this is a short observation, not a leak proof.

## Reproduce ONLY on the disconnected spare

Normal build/update first:

```sh
bash scripts/build.sh
python3 scripts/ota.py SPARE_IP build/garden_native_probe.bin
```

Build the separate diagnostic image, which drives pins on every boot:

```sh
bash scripts/build.sh -B build-io \
  -DSDKCONFIG="$PWD/build-io/sdkconfig" \
  '-DSDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.io-test.defaults'
python3 scripts/test_io_hardware.py SPARE_IP --confirm-disconnected-spare
```

The helper checks the expected normal image first, installs the diagnostic once,
checks results, then restores verified normal firmware in `finally`. It inspects
state before restoring and does not blindly replay uncertain uploads. An unknown
or unreachable state requires inspection/recovery; **do not connect equipment**
until normal firmware is verified. Never run the diagnostic on a live controller,
with external loads/sensors connected, or on an unverified endpoint.

Pure API checks (no physical selftest invocation):

```sh
python3 scripts/test_io_plan.py SPARE_IP
```

At the I/O checkpoint: normal image **922,240 bytes**, diagnostic **943,968 bytes**.
See README.md/FIRST_RELEASE.md for the newer shared-engine image.
Normal `sdkconfig` has both GPIO selftest and pending-boot-failure options disabled.

## Remaining integration and migration gates

1. Subsequent guarded backend integration is implemented; see GPIO_BACKEND.md.
   Its lifecycle/failure paths were exercised against RAM, and controller code
   only compiled. Complete the remaining software gates before hardware testing.
2. Verify switch wiring and relay modules on a bench; validate application boot
   levels as well as reset/power-loss electrical behavior. Sensor measurements
   are deferred and do not block the first relay-only release.
3. Confirm production timezone/DST and schedule behavior before connecting the real
   clock service to actual outputs. Existing rules retain tested simulation coverage.
4. Complete identity/settings/provisioning and config export/restore interfaces.
5. Extended Wi-Fi/network/rule/watchdog stress and OTA power/schema failure tests.
6. Obtain a full recovery path and fresh backups before an approved live-unit
   maintenance window. Even entering a serial bootloader to read flash can reset
   a live controller and change its outputs; an API backup is not a full dump.

None of these bench results authorize or establish readiness to flash the live units.
