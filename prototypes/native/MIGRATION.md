# Live-controller migration preparation

Verified 2026-10-14. This milestone did **not** reflash, change settings, toggle
outputs, synchronize time, or upload code on either live controller.

## Private recovery material

Read-only snapshots for Sunroom2 and Barn are retained under
`/var/lib/private-services/agent-state/jeremy/garden-device-backups/`, in the
mounted encrypted private-services vault, with owner-only permissions. Exact
addresses, configurations, relay labels/rules, Wi-Fi status and device status
remain there, not in Git. The backup script refuses an unmounted vault rather
than falling back to ordinary storage.

Both captures succeeded for all seven API routes: identity, sensor pins, relay
configuration, live sensor values, system status, Wi-Fi status and board list.
Each source snapshot has a SHA-256 manifest. These are sequentially sampled API
snapshots, **not** a firmware dump, filesystem backup or complete `config.json`.
Wi-Fi passwords were deliberately not retrieved. Existing deployed firmware
version/source correspondence and a full restore path are still unverified.
Before any actual flash, obtain a complete recovery method through the correct
physical device, with fresh checks and a controlled maintenance window.

## Prepared simulation profiles

`prepare_migration.py` verifies snapshot checksums and creates
`native-simulation-profile.json` beside each private source backup. It recognizes
only reviewed Python rule AST shapes; unknown rules fail closed. It does not
execute source while preparing a profile. Diagnostic print statements are
removed, and the recognized logic is translated to Lua.

- All 8 Sunroom2 relay definitions and 9 Barn relay definitions were preserved.
- The four scheduled rules were translated; other rules are constant-on or empty.
- Copied-profile pins/inversion remain metadata in the simulator. A separate,
  explicitly enabled diagnostic has tested the HAL on GPIO4/5; it never applies
  copied profiles to hardware and normal firmware is restored afterward.
- Boot defaults are used, not captured momentary current value/automatic mode.
- Original sensor-pin definitions and observed timezone/time are recorded in the
  private profiles for later physical-driver work, not applied as hardware setup.

The simulator now supports up to 16 outputs and the board definition's allowed
GPIO numbers as identifiers. Actual pin writes remain absent. All relays consume
one current/previous input snapshot per automation cycle; previous readings advance
once after evaluating the full relay list, not once per relay.

## Verified rule/config tests

`test_migration.py` ran on the USB spare, not the live controllers:

- **85 deterministic snapshot comparisons** covering constant rules and every
  scheduled rule: switch on/off/held, exact schedule boundaries, before/after
  boundaries, midnight, forward/backward jumps and conflicting switch/time events.
- Valid-clock results compared to the reviewed original Python AST logic with
  restricted builtins and diagnostics removed.
- Explicit invalid-clock behavior: skip schedule evaluation, preserve switch-edge
  functionality; first valid clock has no synthetic catch-up event.
- Each full private relay profile loaded into the simulator, survived an actual
  spare reset and restored every relay's default output/automatic mode, inversion,
  identifier and rule.
- The spare's original simulated configuration was restored after the tests.
- USB regression and actual HTTP smoke tests passed on the updated image.
- Fourteen firmware boot self-tests passed during resets.

Snapshot evaluation (`POST /api/bench/evaluate`) is isolated from runtime inputs,
outputs and persisted settings. `POST /api/bench/inputs` can deliberately change
simulated runtime readings. Missing numeric readings and invalid/uninitialized
clock return Lua nil; `time(h,m,s)` validates its arguments.

These are logical profile tests, not verification of the controllers' wiring,
relay contacts or startup transients. Subsequent isolated HAL, clock/DST and OTA
results are documented separately; physical sensor operation and continuous
watchdog coverage still require work.

## Clock discrepancy requiring a decision

Both live controllers reported `America/Los_Angeles` with a fixed UTC-8 offset.
Their reported clock times differed by approximately seven hours during the
sequential capture; Barn also reported a negative uptime. Do not treat the reported
clock/uptime as trustworthy or infer a cause from these observations alone.

The intended timezone/DST policy must be confirmed. Real SNTP diagnostics and
DST conversions are now tested on the spare, but clock-discontinuity handling and
production rule integration are still needed before migration. Current translated
rules preserve valid-clock source behavior, including on taking precedence if a
large forward jump crosses both the on and off thresholds. That behavior may be
undesirable and needs an explicit policy decision rather than an unnoticed change.
The simulator intentionally starts with an invalid clock, preserving boot defaults
until an explicit valid input is provided. No real NTP or timezone update has been
applied to either live device.

## Reproduce (private folders never go into Git)

```sh
python3 scripts/backup_live.py EXPECTED_HOSTNAME=IP [EXPECTED_HOSTNAME=IP ...]
python3 scripts/prepare_migration.py PRIVATE_SNAPSHOT_DEVICE_FOLDER [...]
sudo "$HOME/.espressif/python_env/idf5.5_py3.12_env/bin/python" \
  scripts/test_migration.py PRIVATE_SNAPSHOT_DEVICE_FOLDER [...]
```

The final command resets and changes ONLY the verified simulated USB spare. It
restores its initial relay configuration in `finally`. Do not run against an
unverified serial endpoint or production firmware. Do not bulk publish private
snapshots, profiles, credentials or device addresses.

## Remaining before a live migration

1. Confirm timezone/DST and integrate the tested clock service with explicit
   schedule behavior around boot/time corrections.
2. Integrate the implemented relay/debounced-input/AHT21 HAL with the runtime.
   GPIO4/5 readback and absent-sensor handling passed on the disconnected spare;
   verify actual sensors, switch wiring, relay modules and output safety policies.
3. Complete settings API and provisioning/export/restore procedures.
4. Extend the now-tested spare OTA/rollback path with power-loss/schema tests;
   establish an attended initial update/full recovery path for the live units.
5. Long-running Wi-Fi/network load, rule containment and failure-injection tests.
6. Fresh final backups; migrate one controller at a time during an approved window.

See [OTA_AND_CLOCK.md](OTA_AND_CLOCK.md) and [IO_DRIVERS.md](IO_DRIVERS.md) for
subsequent spare-only results. The original private snapshots are unchanged.
