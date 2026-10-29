# OTA and real-clock bench results

Subsequent shared-engine work optionally feeds real synchronized time to
memory-only outputs; see [FIRST_RELEASE.md](FIRST_RELEASE.md). The clock separation
below describes this earlier checkpoint. Normal mode still defaults to manual
snapshots and never drives physical relay outputs.

Verified on the disconnected USB spare, 2026-10-14. Neither live controller was
changed. The normal runtime remains simulation-only. A subsequent HAL diagnostic
has exercised spare-only GPIO4/5 and missing I2C; see [IO_DRIVERS.md](IO_DRIVERS.md).
The final running image is normal, with both fault and physical-test flags disabled.

## OTA implementation

- `POST /api/ota/upload`: raw application binary, with required
  `X-Firmware-SHA256` (64 hex characters). No multipart form or HTML frontend.
- `GET /api/ota/status`: running/boot/update slots, validity states, full ELF
  SHA-256, healthy/uploading flags and per-boot diagnostic identity.
- Stream into the inactive 3 MiB slot, not RAM; bound size, receive waits and
  overall upload duration (120 seconds). Boot selection is unchanged on rejection.
- Reject wrong format, chip family and project name before beginning the update.
- Verify transport digest and ESP-IDF image integrity/compatibility before selecting
  the new boot slot. These checks are **not** signatures or authentication.
- Prepare the reboot task before committing boot selection, reply, then notify it
  to reboot. A lost reply may still mean the update happened; clients inspect status
  and never blindly resend an upload.
- A pending boot must pass all firmware self-tests and establish local runtime
  progress: automation/network/USB heartbeats plus sufficient free heap, observed
  for at least five seconds. It is not marked valid immediately on entry to main.
- Failure to establish health within 30 seconds rejects a pending image; actual
  task panic/reset before confirmation also uses bootloader rollback.
- Wi-Fi connectivity and internet/NTP availability are deliberately not prerequisites
  for boot validation. Losing the AP should not itself reject otherwise working code.

This checkpoint describes local boot validation, not proof of long-term stability.
Subsequent continuous application-progress monitoring is described in
RUNTIME_WATCHDOG.md; it is not an independent hardware watchdog or a network
reachability guarantee. Config migrations/rollback compatibility still need
careful design before changing the production schema.

Jeremy explicitly selected unauthenticated trusted-LAN access, including OTA.
Anyone able to reach the endpoint can replace the firmware. Do not forward it to
the internet. No security eFuses were changed.

## Verified OTA cases

1. Successful LAN upload switched slots, booted the expected full ELF digest and
   reached valid/healthy state; relay configuration and Wi-Fi provisioning retained.
2. Wrong format/project rejected.
3. Correct image with wrong supplied digest rejected without changing boot slot.
4. Correct supplied digest with corrupted embedded image integrity rejected.
5. TCP disconnected after a valid image prefix; partial staging cleaned up and
   the previous firmware/configuration continued running.
6. A dedicated image with `CONFIG_BENCH_OTA_FAIL_PENDING_BOOT=y` intentionally
   rebooted while pending. Bootloader restored the previous valid firmware; the
   failed slot reported `aborted`. Recovery succeeded repeatedly.
7. A normal update after rollback reused the inactive slot successfully.

The initial success verifier timed out even though the device successfully updated:
ESP-IDF's convenience hash function returned only its short configured logging
prefix. This was diagnosed by inspecting actual slot/validity state, not by replaying
the upload. Status now formats all 32 digest bytes from the application descriptor.
A per-boot identifier additionally prevents confusing stale rollback status with
an observed new reboot.

Not tested: physical power interruption during erase/write/boot-selection commit,
low-voltage brownout, prolonged radio outage during upload, incompatible future
configuration schemas, signature verification or unauthorized-client protection.
TCP interruption is not a substitute for power-loss testing.

## Run on the verified spare only

```sh
bash scripts/build.sh
python3 scripts/ota.py SPARE_IP build/garden_native_probe.bin
python3 scripts/test_ota_rejection.py SPARE_IP build/garden_native_probe.bin
```

The updater checks simulated spare identity, only uploads once, then verifies slot,
full digest, boot validation, relay config, Wi-Fi provisioning and available clock
settings. Rejection tests overwrite ONLY the inactive slot, not the running app.

Rollback test, **never a production/USB bootstrap image**:

```sh
bash scripts/build.sh -B build-rollback \
  -DSDKCONFIG="$PWD/build-rollback/sdkconfig" \
  '-DSDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.rollback-test.defaults'
python3 scripts/ota.py SPARE_IP build-rollback/garden_native_probe.bin --expect-rollback
python3 scripts/ota.py SPARE_IP build/garden_native_probe.bin
```

The separate normal `sdkconfig` has the fault option disabled. Normal and fault
build artifacts are gitignored. USB bootstrap and recovery remain possible on the
spare, but after OTA changes slots do not assume a raw write at `0x20000` updates
the currently selected image. Inspect slot state; prefer the tested OTA path.
No update/recovery route for the existing live MicroPython controllers has yet
been established.

## Real clock service

SNTP synchronizes UTC through `pool.ntp.org` after Wi-Fi obtains an address and
restarts following reconnects. It does not use IP geolocation or infer a timezone.
Default persisted timezone is **unconfirmed**; internal UTC formatting is not
permission to choose a production schedule timezone.

- `GET /api/time/status`: UTC synchronization, configured zone, local date/time,
  DST, last sync age, synchronization count and clock generation.
- `GET /api/time/zones`: supported explicit names: UTC, America/Los_Angeles,
  America/New_York. The US zones use POSIX transition rules including DST.
- `POST /api/time/config`: `{ "timezone": NAME }`, or null to unset. Saves in a
  separate NVS namespace. Unknown zone names are rejected.
- `POST /api/bench/local-time`: pure conversion of an integral `unix_seconds`
  timestamp from 2020..2100 in the explicitly configured zone. Never changes UTC,
  the simulation's inputs or relay state.

`feeds_simulated_rules` is always false. Actual synchronized time is separate from
controlled Lua snapshots: copied relay schedules do not suddenly run against NTP.
Missing timezone invalidates the real scheduling-clock readiness flag even when
UTC is synchronized. Clock-generation metadata is available for future schedule
baseline/discontinuity handling; the real clock is not wired to production rules.

Verified: SNTP time aligned with the shelf clock; current-date UTC/Los Angeles/New
York conversions matched host zoneinfo; **24 conversions across spring-forward and
fall-back boundaries** matched host zoneinfo; configured timezone survived a spare
reset. The test restored the original unconfirmed timezone and left simulated
rule timestamps invalid/unchanged. It did not set either live controller's clock.

```sh
sudo "$HOME/.espressif/python_env/idf5.5_py3.12_env/bin/python" \
  scripts/test_clock.py SPARE_IP \
  --reset-port "$GARDEN_BENCH_PORT"
```

Still needed: Jeremy's intended production timezone and scheduling policy for
boot, missing clock, large corrections and repeated/skipped local hours; real
schedule integration and extended offline/clock-drift tests. The observed live
clock discrepancy remains unexplained, not silently copied into the replacement.

## Current state

At the OTA/clock checkpoint the application was 919,344 bytes. The current normal
image at the profile checkpoint was 929,728 bytes. See GPIO_BACKEND.md/README.md
for the current image and subsequent results; PROFILES.md describes the new
OTA configuration-contract check. USB/API regression, the 85 private-profile
snapshot comparisons, profile persistence/defaults and HTTP checks passed after
OTA/clock additions. A network-active 200-validation sample was 203,976 -> 203,984
bytes free heap (small concurrent network fluctuation, not a leak proof). This is
bench progress, not approval to flash either live controller.
