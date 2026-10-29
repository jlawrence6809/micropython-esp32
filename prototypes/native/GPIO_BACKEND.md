# Relay backend integration — software milestone

**2026-10-28 target extension:** original ESP32 now has a separate compile-time
pin policy and4MiB candidate build; S3 policy/hash/activation remain unchanged.
Shared real backend/profile/commit host fault tests pass for both targets. This
is NOT original-ESP32 hardware commissioning. See [ORIGINAL_ESP32.md](ORIGINAL_ESP32.md).
The dated milestones below retain their original scope.

Verified 2026-10-14 on the authorized spare. Only normal memory-only firmware was
loaded. Controller firmware was compiled, NOT booted or armed. No application
GPIO diagnostic ran and neither live unit was accessed or changed.

## Shared resource coordinator

`main/io_backend.c` owns relay/input lifecycle through a driver-operations table.
The GPIO implementation and fault-injectable RAM implementation use the same
planning, rollback, command and cleanup code.

- Validate the entire profile and all pin conflicts before invoking any driver.
- Establish input baselines before enabling relay outputs.
- Initialize relay levels from defaultValue with inversion respected.
- Track attempted opens, including partially failed ones; release every touched
  resource on failed initialization. Retain failed cleanup ownership and refuse
  reuse until cleanup succeeds. Never pretend partially initialized pins vanished.
- Writes update cached logical state only after SDK success. Publish that state,
  not an optimistic requested value, after partial multi-relay write failures.
- Unknown pins, inversion mismatches and changed live layouts fail before writes.
- A live output batch is NOT electrically atomic: earlier successful commands can
  remain applied when a later command fails. The profile is already persisted;
  responses include outputs_applied=false plus warning, and the failed relay has
  last_error. Garden must surface this and refresh rather than blindly retry.

Cleanup disables output and releases pulls. It does not establish that actual
relay contacts de-energize: external bias, module polarity and reset/ROM behavior
still require attended electrical tests.

## Bench and controller are separate build families

Normal build:

- CONFIG_GARDEN_CONTROLLER_IO disabled, physical operations table absent.
- Contract native-profile1; role development-bench; memory-only output model.
- USB io_arm/io_disarm rejected even with a valid layout hash/confirmation.

Controller build:

- CONFIG_GARDEN_CONTROLLER_IO enabled, contract relay-profile1, role relay-controller.
- Runtime rejects a mismatched build contract BEFORE any GPIO initialization.
- Physical bench diagnostic and controller mode cannot be enabled together.
- Starts UNARMED without a matching persisted commissioning record.
- Bench HTTP/USB clients reject even an unarmed controller reporting simulated=true.

A controller build compiles separately:

```sh
bash scripts/build.sh -B build-controller \
  -DSDKCONFIG="$PWD/build-controller/sdkconfig" -DPROJECT_VER=relay-profile1 \
  '-DSDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.controller.defaults'
```

This is a compile command, NOT permission to flash a controller. It was only
compiled in this milestone. The normal bench OTA endpoint rejected the actual
controller image's different contract before staging it.

## USB commissioning interlock (not exercised on a controller yet)

GET /api/io/status reports compiled/active mode, layout hash, chip identity and
whether the saved layout is armed. The layout hash binds relay order/pins,
inversion, boot value/auto defaults, all input reservations, timezone, clock source
and schedule policy. Current values/auto flags, labels, rules and hostname are
excluded so ordinary controls/editing do not require re-arming. JSON property order
does not affect the fingerprint.

A controller USB io_arm command requires the exact device ID, current layout hash,
explicit phrase, validated boot health, configured network clock/timezone, and at
least one relay. The single NVS arming record binds BOTH factory chip identity and
layout. Profiles do not contain it; copying a profile or raw backup to another
chip does not arm that chip. Missing, wrong-chip or stale-layout records leave GPIO
inactive. Invalid storage errors fail closed without erasing data.

Arm/disarm changes apply AFTER reboot, never by hot-reconfiguring outputs. Disarm
does not immediately change currently active outputs. Active layout/default/clock
changes return 409 until explicit USB disarm + reboot, followed by configuration
and re-arming. Armed same-layout imports preserve the clock baseline so ordinary
edits do not suppress an upcoming legitimate schedule edge. Ordinary value/auto/rule/label edits remain possible while armed.
There is no HTTP arming endpoint.

scripts/controller_io.py is USB-only, verifies the controller role, requires
operator maintenance confirmation plus expected boot/device/layout identifiers,
and NEVER issues a reboot command. All its USB actions, even status, require a
maintenance acknowledgement: opening an adapter can itself reset the controller.
Do not invoke arming until the software release gates and attended hardware plan
are ready.

These are accidental-activation interlocks, not authentication. LAN APIs and OTA
remain unauthenticated by deliberate user choice; unsigned custom firmware can
bypass software interlocks. No new passwords, signatures or credential tokens.

## Inputs, time and sensors

Controller input initialization waits for a stable 40 ms baseline, with a bounded
200 ms noise timeout after initial pull settling, BEFORE outputs open. A separate
~10–20 ms sampler feeds debounced states into the existing 500 ms automation loop.
Both current/previous switch values start from that baseline: no invented boot edge.
Latching wall switches are the target; this is not an event queue for arbitrarily
short momentary presses between automation snapshots.

Real controller mode always uses the configured network clock. Missing initial
sync suppresses copied schedule edges, not switch operation or local boot health.
The tested discontinuity baseline behavior is unchanged. Actual sensors remain
optional/deferred; real mode reports missing temperature/humidity/light, never the
bench's demo readings. I2C pins are only reserved, no AHT21 probe or calibration is
required for relay-only startup.

Boot validation now requires heartbeats from rules, network, USB AND input sampler.
Subsequent continuous progress monitoring and actual task-stall recovery tests
are documented in [RUNTIME_WATCHDOG.md](RUNTIME_WATCHDOG.md). This is not a guarantee
of network reachability or an independent hardware watchdog.

## Verified software coverage

Pure backend tests run each boot and through POST /api/bench/backend-selftest:

- Full startup/defaults, initial switch state and no invented edge; missing sensors.
- Debounce through the RAM driver.
- Partial first/second relay-open failure and switch-open failure, with cleanup.
- Cleanup failure retained, restart blocked, cleanup retry successful.
- Failed output leaves old state, recovery succeeds, bad pin/inversion rejected.
- Partial manual batch publishes only successful commands and flags failure.
- Conflicting plans and changed batch pin layouts produce zero driver calls.
- Arming record refuses changed chip/hash and malformed records.

scripts/test_backend.py additionally verifies immutable bench/controller role
separation, USB/HTTP activation refusal in normal firmware, fingerprint exclusions
and bindings, and profile unchanged after all tests. This is NOT proof that the
controller-only activation path or actual relay hardware has been exercised.

Full regression passed: profiles/boot-write gate, shared engine/manual/clock
behavior, USB, 85 private reference comparisons, both simulation profiles, 24 DST
conversions, HTTP, I/O plans, OTA corruption/interruption/contract rejection,
pending-failure rollback and subsequent normal update. Original profile restored.
A short 200-validation heap sample was stable, 197,988 -> 197,988 bytes.

At this backend checkpoint: normal 937,840 bytes, controller compile-only 942,208.
See README.md for the current image after continuous-watchdog additions.
Current spare: normal valid/healthy image, original hostname, unconfirmed timezone,
manual clock, no compiled GPIO adapter and no physical tests enabled.

## Remaining before hardware-test readiness

- Actual Garden phone testing/review/publishing. Atomic partial-update APIs and
  native AUTO/config/rule autosave are now implemented and tested on the memory-only
  spare; see ATOMIC_EDIT.md. No phone deployment or actual-controller test yet.
- Controller-safe commissioning/profile/update tooling and reviewed recovery steps.
- Extended network/idle/reconnect/power testing and investigation of intermittent
  HTTP read timeouts. Initial continuous-watchdog/adversarial tests now pass.
- Confirm intended production timezone/boot scheduling policy at commissioning.

Then, with explicit operator coordination: full live backup/recovery preparation,
module/wiring/polarity/reset/brownout checks, and one controller at a time. Sensor
hardware still does not block the first relay-only release.
