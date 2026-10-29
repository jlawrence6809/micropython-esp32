# Native ESP32 / ESP32-S3 prototype

## Source checkpoint — 2026-10-29

The dated milestones below are historical, not blanket current-state claims.
Two original-ESP32 Relay_X8 boards now have separate verified original-flash
backups, healthy native firmware, Wi-Fi and successful guarded OTA. The first is
operator-wired in the Sunroom: GPIO33/K2 = Sunroom lights, GPIO25/K3 = Outdoor
lights, other functions not inferred from old array order. All relay values/AUTO/
boot defaults were last verified OFF. GPIO18 switch input was enabled live with
pull-up/debounce and preserved hardware enablement; operator toggle and light
rule still pending. The second remains an unarmed bench spare. Existing Barn
ESP32-S3 is unchanged by these replacement-board tasks. Recovery and exact status:
[ORIGINAL_ESP32.md](ORIGINAL_ESP32.md), [LIVE_SWITCH_INPUTS.md](LIVE_SWITCH_INPUTS.md),
[CONTROLLER_OTA.md](CONTROLLER_OTA.md). No production Garden/phone publication.

Firmware source is checkpointed separately from private recovery/build evidence.
Build directories, downloaded dependencies, credentials, raw captures and device
journals are excluded. Host tools require an explicit `--port` or
`GARDEN_BENCH_PORT`; no specific adapter serial is a source default. The private
Wi-Fi worker plan must now explicitly provide `approved_ssid` matching its
credential's SSID. Historical frozen workers/plans remain recovery evidence, not
replay instructions. Single-AP trials likewise require private `--observer-config`
JSON containing approved `observer_host`, `workstation`, `key`, `known_hosts`.
No environment default or source placeholder grants hardware-operation approval.


**2026-10-28 original-ESP32 software preparation:** selectable `--target esp32`
keeps existing S3 builds/pin policy/layout intact. Original-ESP32 and S3 controller
builds compile and pass offline image/target/backend guards. Candidate4MiB layout,
UART0 setup, target-specific GPIO/OTA checks and inert Relay_X8 starter profile:
[ORIGINAL_ESP32.md](ORIGINAL_ESP32.md). No original-ESP32 hardware opened/flashed,
no output activation and no installed controller updated in this software task.


**2026-10-27 Sunroom diagnostic update:** One explicitly approved AC-OFF/unarmed
OTA succeeded, GPIO/profile/clock retained. Read-only AP/BSSID/channel/PS and
32-event volatile history now available. Captured strong-signal OpenWrt missing-
ACK disconnect followed by eventual Deco connection; cause not yet proven, no
network policy/power-save changes made. See [WIFI_DIAGNOSTICS.md](WIFI_DIAGNOSTICS.md).

**Current release scope:** relay/manual/schedule functionality first; optional
sensor hardware comes later. See [FIRST_RELEASE.md](FIRST_RELEASE.md) for the
software/hardware gates and current shared-engine behavior. Application profiles
and provisioning are documented in [PROFILES.md](PROFILES.md). Guarded output
backend integration and separate controller build: [GPIO_BACKEND.md](GPIO_BACKEND.md).
Continuous application progress monitoring, real task-stall recovery and initial
HTTP stress/deadline tests: [RUNTIME_WATCHDOG.md](RUNTIME_WATCHDOG.md).
Guarded OTA reservation: [GUARDED_OTA.md](GUARDED_OTA.md). Attended unarmed-controller
uploader and verified Sunroom2 Wi-Fi update: [CONTROLLER_OTA.md](CONTROLLER_OTA.md).
Barn now has verified native USB setup, all 9 definitions/Lua restored and Wi-Fi
connected, with healthy unarmed state verified over USB and LAN. Profile/Wi-Fi
also survived an observed subsequent USB reset, activating hostname `barn`.
A subsequent circuit-powered LAN boot and approved Seattle/LA synchronized
network clock are verified. Subsequently, under explicit main-OFF/native USB
approval, Barn's manual-OFF test layout was USB-armed and GPIO activation
verified after operator USB replug. Subsequently main power was restored under
attendance; Overhead API ON physically confirmed and app control reported working.
Requested daily Seattle 08:00 ON / 20:00 OFF rule/current AUTO enabled, wall-switch
logic retained. On 2026-10-26 Jeremy explicitly approved lights-only remote OTA
and live settings. One armed OTA succeeded with healthy new image/GPIO/clock and
configuration preserved. Live polarity/startup-default edits now supported;
Overhead startup AUTO saved true and Flood light polarity corrected, others
unchanged. No subsequent reboot test of that new startup default or physical
Flood polarity confirmation yet. See [LIVE_RELAY_SETTINGS.md](LIVE_RELAY_SETTINGS.md)
and BARN_BRINGUP.md; no old main-OFF isolation applies. Broader physical tests and
power-loss/rollback proof remain pending; USB opens may restart hardware.
See [NATIVE_USB_SETUP.md](NATIVE_USB_SETUP.md) and the preserved migration history
in [BARN_BRINGUP.md](BARN_BRINGUP.md). Do NOT replay old bootstrap/restore journals.
Maintenance/recovery review: [COMMISSIONING.md](COMMISSIONING.md). Accepted deferrals and operational
limitations: [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

Local branch: `prototype/esp-idf-lua`. Updated 2026-10-20.

**Not yet commissioned for live equipment.** Jeremy physically isolated Sunroom2
and authorized its initial USB migration. Its original full flash was verified
and preserved privately; the separate native controller image, eight-relay Lua
profile and Wi-Fi are installed, with successful healthy boots and persistence
checks. **GPIO has never been armed.** One guarded Wi-Fi update/software reboot and its
configuration/clock retention passed while Sunroom2 was bare/unarmed; the executor
still refuses active-output updates pending physical commissioning. Barn is
unchanged as of that Sunroom2 milestone; see BARN_BRINGUP.md for its subsequent
2026-10-20 migration and NATIVE_USB_SETUP.md for its working USB/LAN restore.
Sunroom2 remains unarmed; Barn is GPIO-active on live equipment with Overhead
ON/app control confirmed and 08:00/20:00 current AUTO enabled. Broader contact/
load commissioning and scheduled real-time edge observation remain outstanding. Sunroom2's physical
RET/reset issue is explicitly deferred at Jeremy's request; see HW-001 in
[KNOWN_ISSUES.md](KNOWN_ISSUES.md). Do not infer live-output approval from this
migration or deferral.

The default bench runtime described below remains memory-only. A native HAL and
separate controller build exist. Prior isolated spare diagnostics tested GPIO4/5
and absent I2C on GPIO1/2; they did not validate relay contacts or actual wiring.
See [IO_DRIVERS.md](IO_DRIVERS.md) for the exact tests and limitations.

## Dependencies and build

- ESP-IDF v5.5.1, ESP32-S3 (default) or explicit original ESP32 target, built on Fedora Asahi ARM64 with Python 3.12.
- Lua 5.4.8, official mirror commit
  `6e22fedb74cf0c9b6656e9fce8b7331db847c605` (MIT license in vendor checkout).
- Espressif mDNS 1.8.2; dependency resolver lock is tracked.

Install ESP-IDF v5.5.1 and its ESP32-S3 tools, then:

```sh
bash scripts/build.sh
```

`IDF_PATH` and `IDF_PYTHON_ENV_PATH` override shelf defaults. Lua is fetched and
revision checked by the script; vendor checkout and build artifacts are ignored.
Binary: `build/garden_native_probe.bin`.

Flash ONLY a freshly verified, authorized spare. `build/flash_args` includes the
bootloader, partition table, initial OTA selection and app, replacing existing
firmware/layout. Do not use it on live controllers. Two 3 MiB app slots and boot
rollback are configured. Streaming LAN updates, boot health confirmation,
rejected/interrupted uploads and deliberate failing-boot rollback have now been
tested on the spare. See [OTA_AND_CLOCK.md](OTA_AND_CLOCK.md) for exact coverage,
commands and remaining power-loss/schema-compatibility limits.

The shelf user lacks root:dialout serial access. Initial flash/serial tests used
narrowly scoped `sudo -n` commands; no group, permission, udev, host service or
network changes were made. Use the stable by-id port, not a guessed tty number.

## USB setup (no password in source/chat)

Run interactively on the shelf over SSH, while no other process owns this port:

```sh
sudo /home/jeremy/.espressif/python_env/idf5.5_py3.12_env/bin/python \
  /home/jeremy/code/micropython-esp32/prototypes/native/scripts/usb.py provision
```

The helper verifies simulated bench identity, prompts for the 2.4 GHz SSID and a
hidden password, sends them directly over USB without echoing/logging input, and
waits for an IP. Empty password means an open network; supported WPA password
length is 8..63 bytes. It uses DTR/RTS deasserted on open. No credentials are
embedded in the binary or host files. NVS stores one Wi-Fi configuration blob
atomically across updates, separate from firmware. **NVS is currently unencrypted**;
this is not secure storage against physical flash extraction. RAM cleanup is
best-effort, not guaranteed elimination of every library copy.

```sh
# Safe status; excludes password
sudo /home/jeremy/.espressif/python_env/idf5.5_py3.12_env/bin/python \
  /home/jeremy/code/micropython-esp32/prototypes/native/scripts/usb.py status
```

Hostname: `garden-bench`; advertises `_http._tcp` on port 80 via mDNS. No setup AP
is started. If `.local` resolution fails, use the IP from USB status.

Wi-Fi has automatic reconnect with capped exponential backoff (1..32 seconds)
and a connection-attempt retry deadline. Status exposes IP, SSID, RSSI,
disconnect counter and most recent numeric disconnect reason, never password.
Jeremy provisioned the spare interactively. LAN HTTP smoke checks passed on
2026-10-08 and again after the 2026-10-14 update. Provisioned Wi-Fi reconnected
after spare resets in regression tests. Extended disconnect/backoff stress and
mDNS name resolution still need work; the shelf's direct mDNS query timed out.
No password was retrieved from either live controller.

## HTTP API and USB test transport

No HTML assets, TLS, tokens or login. Jeremy explicitly selected trusted-LAN
access, including OTA. Anyone who can reach these endpoints will
be able to modify the device; image checks/rollback are reliability protections,
not authentication. Do not expose this server to the internet.

Implemented routes:

| Route | Behavior |
|---|---|
| `GET /api/config` | Bench identity, `rule_language: lua`, `simulated: true` |
| `GET /api/status` | Garden-compatible key/value array: uptime, reset reason, heap, disconnects, evaluations |
| `GET /api/wifi/status` | Connection diagnostics, no password |
| `GET /api/sensors` | Simulated temperature 23, switch false, other sensors null |
| `GET /api/gpio/available` | Allowed board GPIO numbers used as simulation identifiers; no physical outputs |
| `GET /api/relays/config` | Relay array with existing Garden field names, errors and simulated flag |
| `POST /api/relays/config` | Validate/persist up to 16 simulated relays as one NVS string; no physical GPIO writes |
| `POST /api/validate-rule` | Raw text Lua, evaluated against simulated inputs without changing outputs |
| `POST /api/bench/evaluate` | `{rule, inputs}` deterministic snapshot evaluation; result 1/0/-1/-2 = on/off/hold/error; does not change runtime inputs or outputs |
| `POST /api/bench/inputs` | Update simulated readings only, no physical input/output operations |
| `GET /api/ota/status` | Slots, validity, full firmware digest, per-boot ID and local runtime health |
| `GET /api/ota/fence` | Public boot/config/arming consistency token; not authentication |
| `POST /api/ota/upload` | Inactive-slot integrity checks and reserved reboot/rollback; matching fence mandatory on controller builds |
| `GET /api/time/status` | Real SNTP/UTC/timezone diagnostics, separate from simulated rules |
| `GET /api/time/zones` | Supported explicit timezone names |
| `POST /api/time/config` | Persist explicit timezone, or null to leave unconfirmed |
| `POST /api/bench/local-time` | Pure timestamp conversion for clock/DST tests |
| `GET /api/watchdog/status` | Continuous task progress, ages/reset masks, diagnostic flags |
| `GET /api/io/status` | Compiled/active GPIO mode, chip/layout binding and arming metadata |
| `POST /api/bench/backend-selftest` | RAM-only resource/failure tests; never physical GPIO |
| `GET /api/profile/edit` | Current profile + opaque edit revision and boot ID |
| `POST /api/profile/patch` | Atomic partial edits with conflict/boot/layout guards; see ATOMIC_EDIT.md |
| `GET /api/profile` | Canonical credential-free application profile export |
| `POST /api/profile/validate` | Pure full-profile/pin/schema validation |
| `POST /api/profile/import` | Persist full profile; no GPIO activation; identity deferred to reboot |
| `GET /api/engine/status` | Shared control-loop counters, memory-only levels and clock source |
| `POST /api/bench/engine-run` | Isolated shared-engine tests with clock/output failure injection |
| `POST /api/bench/clock-source` | Volatile manual/network clock selection; never enables GPIO |
| `POST /api/relays/control` | Manual label/state command; disables auto for that relay |
| `GET /api/bench/io-status` | Boot I/O tests, diagnostic flag and test-pin release status |
| `POST /api/bench/io-plan` | Pure pin/conflict validation and computed startup levels; no hardware/settings applied |

Other routes return 404, not fake successes. Sensor-pin settings, board/hostname
editing, Wi-Fi scan/connect over HTTP, manual time-of-day setting, storage and a
standalone restart route are not implemented. Garden's existing relay editor help/examples still describe
Python; use explicit Lua `return` statements for this device. No Garden files
were changed in this milestone.

Input bounds: JSON/text HTTP body <=12 KiB (binary OTA <=inactive slot size),
rule <=2048 bytes, JSON nesting <=16, labels
<=48 bytes, unique allowed simulation identifiers/labels, required boolean fields. HTTP has
bounded sockets, receive timeout and LRU socket cleanup. USB newline JSON uses
request IDs to match responses; it shares the actual API dispatcher for bench
testing without a network connection. Mutating requests are never blindly retried.

Relay configuration is committed before swapping live simulated state; schema
version 1 is recorded and unknown versions are refused, not silently erased.
On boot, current value/auto are restored from `defaultValue`/`defaultAuto`.
Automation runs in a separate task every 500 ms, with state protected by a mutex.
Errors preserve the simulated output and appear as `last_error`; the next
successful evaluation clears the error. Runtime rule changes do not rewrite
flash every evaluation.

## Rule containment

- Fresh Lua state per evaluation, allocation cap 64 KiB.
- 20,000-instruction limit checked every 100 instructions and cooperative 20 ms
  deadline. **Not a hard wall-time guarantee:** parsing, allocation, cleanup and
  native calls can extend total evaluation time.
- No standard libraries: no OS/filesystem/module/debug/dynamic-loader APIs and
  no exception-catching functions exposed.
- Current/previous temperature, humidity, light level, switch, reset switch, and
  seconds-since-local-midnight helpers are exposed with simulated input.
  `time(h,m,s)` validates ranges. Unknown readings/clock return Lua nil.
- Boolean/nil result contract: on/off/hold; invalid result is an error.

Initial guardrails, not a formally verified sandbox. Watchdog integration,
recursion/adversarial coverage, further memory-pressure testing and real sensor/
switch/time integration are still needed before production use.

## Verified bench tests

Chip ESP32-S3 rev v0.2, 16 MiB flash and 8 MiB PSRAM. This build uses internal RAM
only and default 160 MHz CPU. Current normal app image: **946,144 bytes**.

Fourteen boot tests passed: on/off/hold, syntax error, invalid return, infinite
loop, allocation exhaustion, unavailable OS API/loader, time helper/range checks,
invalid clock, missing sensors and previous-reading helpers. Thirteen additional
pure I/O tests run on normal boots; the dedicated diagnostic adds four grouped
physical tests, then the normal image is restored. See IO_DRIVERS.md. Original
serial-only milestone had typical trivial rule times ~2–3 ms; infinite-loop
termination ~10.7 ms and allocation exhaustion ~23.2 ms including cleanup.

On the network-capable image, USB regression verified:

- Invalid provisioning rejected without changing provisioned state.
- API response shapes and validation does not mutate output state.
- Malformed/deeply nested JSON, duplicate identifiers and disallowed console-pin identifiers rejected.
- Simulated automation turns on, holds during runaway-rule failure, and recovers
  to off when replaced by a valid rule.
- NVS persistence across an actual reset; boot restores per-relay defaults.
- Earlier network-capable build: 200 repeated rule validations with sampled free
  heap **209,888 -> 209,888 bytes**; see updated network-active measurement below.
- Test restores original simulated relay configuration in `finally`.

```sh
# Modifies simulated relay config and resets ONLY the spare during tests
sudo /home/jeremy/.espressif/python_env/idf5.5_py3.12_env/bin/python \
  /home/jeremy/code/micropython-esp32/prototypes/native/scripts/usb.py test

# After provisioning, LAN HTTP smoke test
python3 scripts/http_test.py SPARE_IP
```

Short observations do not establish long-term stability, Wi-Fi reliability,
OTA safety, or exhaustive HTTP correctness. Basic actual HTTP requests passed.
A 2026-10-14 heap regression initially failed because Wi-Fi reconnect allocations
were included immediately after reset. Tests now wait for configured networking
and allow a 4 KiB background fluctuation; rerun sampled 206,300 -> 206,220 bytes.
This is not a strict leak proof.

## Next milestones

1. Garden end-to-end checks, mDNS diagnosis, long-running traffic/reconnect tests
   and bounded-rule watchdog/adversarial tests.
2. Confirm intended timezone/DST and schedule discontinuity behavior. Explicit
   network-clock mode now feeds the shared engine's memory-only outputs; manual
   snapshots remain the default. See FIRST_RELEASE.md for the tested time guard.
3. Exercise the compiled controller path only after the remaining software gates.
   The GPIO/input backend and USB arming interlocks are implemented, with lifecycle
   tests against RAM. Actual wiring, relays and reset/power behavior remain unverified.
4. Actual phone checks/review/publishing for Garden's implemented atomic-edit
   autosave UI (ATOMIC_EDIT.md), plus production commissioning/update tooling.
   Sensor hardware is deferred and does not block the first relay-only release.
5. Extend tested OTA with physical power-loss/brownout and incompatible-schema
   recovery tests; extend the initial progress-monitor/stress coverage and
   investigate intermittent HTTP read timeouts.

Live Barn's earlier intermittent reachability remains unexplained. Both private
relay profiles have now been temporarily loaded/tested on this spare in simulation,
then the original simulated configuration restored. See [MIGRATION.md](MIGRATION.md)
for backup coverage, rule comparisons, clock discrepancies and remaining gates.
