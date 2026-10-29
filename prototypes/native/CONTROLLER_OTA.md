# Guarded controller Wi-Fi OTA

## 2026-10-29: attached-load all-OFF maintenance and live switch inputs

Jeremy approved a simpler input-edit workflow, delivered to the original-ESP32
Sunroom Relay_X8 by ONE guarded OTA under the new explicit
`--all-relays-off-confirmed --remote-reboot-confirmed` policy, plus maintenance/
apply/new vault journal/explicit esp32. This is not a false lights-only or physical
isolation claim: EVERY relay current value/AUTO/startup value/startup AUTO must be
OFF in both preflight snapshots and after reboot. Mutually exclusive with other
alternative policies. Same identity/coherent fence/health/config/activation/clock,
one upload/no replay and physical recovery requirements. Default unarmed policy
unchanged. 32 offline uploader regressions pass, including ON/default rejection,
postboot ON, lost reply, pending disarm and policy/identity conflicts.

965,808byte app SHA `c92871627cbda59b522f6546575ef6a26056d3111029411c08c47384101e3dfb`,
ELF `e481598cdad857b38b35afc586b1b3e1ff96b2fb0a0f42cfbd7ea88c15d70997` switches
ota_1 -> ota_0, new healthy/valid boot, all8 values/AUTO/defaults OFF, labels,
profile/Wi-Fi and active GPIO/arm retained. Subsequent single live input patch
adds GPIO18 while retaining hardware enablement and baselining the held switch;
no UART/disarm/reboot/relay write for that edit. Input baseline false/open, physical
toggle not yet verified. Detailed implementation/failure limits:
[LIVE_SWITCH_INPUTS.md](LIVE_SWITCH_INPUTS.md). Earlier descriptions of all input
resource changes as maintenance-only are superseded ONLY for this bounded all-OFF
switch-input path, not arbitrary relay/clock/environmental sensor remapping.

## Second original ESP32 Relay_X8: independent unarmed OTA verified

Separate board identity/original4MiB verified backup, unique `relay-x8-spare` bench
profile. No live Barn changes. One private Wi-Fi provision/five-minute LAN test
passed before one guarded OTA under explicit original-target/isolated-unarmed
policy. New app964,640bytes SHA
`f287e1db294a9673f58bac33d7c7b4d320b272dfbbb54315fb48777b3eaea491`, ELF
`a367dd594f901b6cd98caf2e5f5fd9e68415238e306542bb856b035a2365c1f5`; same source/SDK
settings, distinct build. ota_0 -> ota_1, expected new healthy/valid boot, profile/
Wi-Fi retained, all8 current/default/AUTO OFF, GPIO inactive and arm false.
No UART open/reset/arm during OTA. Four postboot shelf samples over60.4s plus
independent Drallion GET verify same boot/image/profile/AP and healthy watchdog.

Post-OTA startup had ONE initial reason7 (class3 frame/nonassociated station) at
1.968s, before first association2.570s/IP4.160s. Recovered automatically; counter1
already in executor's confirmed snapshot and unchanged through follow-up. Initial
zero-counter assertion stopped a GET-only check; diagnostics and stopped evidence
preserved, subsequent observation explicitly tests NO ADDITIONAL disconnects.
Do not describe this as zero post-OTA retries, a late established-link drop, or
proof of old Sunroom reason34/root cause. No production/load/forced-rollback test.
See ORIGINAL_ESP32.md and private `current-relay-x8-second.local.json` checkpoint.

## 2026-10-28: original ESP32 Relay_X8 unarmed OTA verified

Jeremy explicitly approved the guarded OTA/reboot test after five-minute Wi-Fi
qualification. This integrated board uses a reviewed12V controller supply with
ALL relay contact terminals empty/no connected powered equipment, not USB power
or a claim of literal bare-board geometry. Used the existing isolated-UNARMED
policy: `--equipment-power-off-confirmed --remote-reboot-confirmed` plus maintenance,
apply/new journal, explicit `--chip-target esp32`, private target with
`expected_device_id` and `chip_target: esp32`. Help now describes a reviewed
maintenance supply; activation/identity/fence/confirmation checks are unchanged.
Never infer authorization for another supply/load arrangement from this bench case.

Fresh isolated original-target controller build uses IDENTICAL firmware source
and assigned SDK settings; only build identity differs. App964,640bytes fits
both1.5MiB slots on4MiB flash. SHA256
`e3cfe5355efd08d7a5b6a02a4a6e2b5c8ca850a17f89f99165cc92b9b5d4bba9`, ELF
`180967eed3428e85691a4c4c046e6399b6943277499d306892868287e95a557d`.
11 original-target/8 release/25 uploader regressions, both-target real blank-NVS/
profile-edit/backend/commit tests and compiler guards pass. Frozen app/ELF/SDK/
source fingerprints and new target/approval/journal live in mounted vault only.

GET-only preflight followed by exactly ONE guarded upload succeeds. New boot
switches ota_0 -> ota_1, expected full ELF, healthy/valid, watchdog timeout0, GPIO
inactive and saved-layout arm false. All8 relay definitions/polarities/defaults/
rules/sensor pins/hostname survive, all current/default/AUTO/defaultAUTO OFF;
manual/unconfirmed clock retained (NOT a network-clock synchronization test).
Wi-Fi credentials retained and DHCP/API recovered with disconnect count0.
No USB open, UART command/reset, physical EN press, arming or settings restore.
Four additional shelf GET snapshots0/10/30/60s and independent Drallion GETs prove
same new healthy ota_1 boot/ELF and unchanged profile/unarmed state. End free heap
134,132/min119,300bytes. See [ORIGINAL_ESP32.md](ORIGINAL_ESP32.md) for bring-up
failures/fixes and prior UART/Wi-Fi qualification.

Private board pointer `native-ota-test-current.local.json` is the CURRENT image
provenance; earlier app-repair plans are historical, not current-image metadata.
Original stock recovery dump and prior known-good app retained. Forced rollback,
power-cut recovery, physical contacts/activation and long-term reliability are NOT
validated by this successful normal update. Production Sunroom/Barn unaffected.

## 2026-10-27: equipment-OFF attached/unarmed maintenance

Sunroom2's diagnostic OTA succeeded once under explicit AC-OFF/USB-power approval,
retaining inactive/unarmed GPIO, profile and clock. A truthful alternative to
literal bare-board confirmation is now `--maintenance-confirmed
--equipment-power-off-confirmed --remote-reboot-confirmed` with apply/target/image/
new journal. This still refuses active or pending-arm controllers; it is mutually
exclusive with lights-only policy. Optional `--verification-timeout 15..600`
extends only GET recovery polling (default120), never upload retries. See
[WIFI_DIAGNOSTICS.md](WIFI_DIAGNOSTICS.md) for tests, evidence and limits.

## 2026-10-26 extension: explicitly approved lights-only remote maintenance

Barn completed one successful armed/lights-connected OTA, expected new healthy
image/slot, GPIO/arming/config retained and clock restored. See
[LIVE_RELAY_SETTINGS.md](LIVE_RELAY_SETTINGS.md) for explicit user scope, image,
tests, limitations and live relay settings. Bare/unarmed remains the DEFAULT;
remote lights-only is an explicit alternative, not a claim of physical isolation.

## Verified milestone — Sunroom2, 2026-10-16

Jeremy explicitly approved proving OTA while the controller was a bare board,
USB-powered on Drallion and within physical recovery reach. GPIO was unarmed.

- Built a diagnostic-free ESP32-S3 `relay-profile1` application, 950,736 bytes.
  The firmware change only adds a credential-free `RUNTIME_STATE` startup summary
  (contract, relay count, GPIO-active flag, clock source and zone-confirmed flag).
  No GPIO, rule, schema, arming or OTA-server logic changed.
- File SHA256:
  `89efc07c6374c0dae52f65aeb1be1afdd5ea0a066662eb99d2153ac5d74c4500`.
  ELF SHA256:
  `65cae0c07d327430d5d32c5b5ca6186c308ffc355b8e20bbc78a05b4c96b1c6b`.
- Two stable GET-only snapshots checked expected chip, image contract/role,
  health, boot selection, cleanup/watchdog state, edit revision, layout and OTA
  fence. Original verified full-flash recovery media remained preserved privately.
- Exactly ONE fenced Wi-Fi POST was sent and acknowledged HTTP 200.
- The application switched `ota_0` -> `ota_1`, rebooted into the expected new ELF
  and reached healthy/valid state. There was no USB open, physical RET press,
  GPIO arming, configuration restore or recovery intervention.
- Post-boot checks verified the eight relay definitions, rules, polarity/defaults,
  boot AUTO state, hostname, sensor/clock configuration, layout, Wi-Fi connection
  and synchronized `America/Los_Angeles` schedule clock. Current relay values are
  intentionally not compared: boot defaults and automation can change them.
- Three additional GET-only snapshots, spaced ten seconds apart, retained the
  SAME healthy new boot, configuration, Wi-Fi network, synchronized clock and
  inactive/unarmed GPIO.
- Eight existing release-audit tests plus sixteen new uploader tests pass offline.

Raw identities, private settings, fences, exact journals, frozen image/sdkconfig,
source hashes and recovery media stay in the encrypted vault, not Git/chat.
This is ONE successful attended UNARMED update, not physical-output commissioning,
a controller rollback/power-cut test, or proof that HW-001 is fixed.

## Tool boundaries

`scripts/controller_release.py` remains a GET-only/offline audit with NO upload,
reset or arm path. Its shared `controller_state()` validator is also used by the
separate executor; its normal audit still rejects an image already running.

`scripts/controller_ota.py` defaults to GET-only inspection and bare/unarmed
execution. Armed updates require the separately approved **lights-only remote**
policy: `--maintenance-confirmed --lights-only-confirmed --remote-reboot-confirmed`
(in addition to apply/target/image/new journal). Both lights/remote acknowledgements
are required. No power equipment, pending arm/disarm or activation mismatch is
permitted. See LIVE_RELAY_SETTINGS.md. Do not bypass either policy using curl or
bench tools; future power-equipment use needs a fresh policy review.

An actual upload in the original bare/unarmed mode requires ALL of:

- `--apply --maintenance-confirmed --bare-board-confirmed --attended-reboot-confirmed`;
- an unlocked vault target JSON with a literal private LAN IPv4 `host` and an
  independently verified `expected_device_id` (never trust hostname/IP alone);
- a reviewed, different-ELF application for the selected chip with the same
  `garden_native_probe` project and `relay-profile1` configuration contract;
  S3 remains the default, original ESP32 requires explicit `--chip-target esp32`
  and matching private target metadata/actual inactive-slot capacity;
- a NEW private `--journal` path, never reused or overwritten;
- coherent healthy unarmed state and stable boot/config/layout/image/fence across
  two snapshots, with no pending arm/disarm/hostname/boot-selection changes.

Example shape, using private file paths rather than raw identities:

```sh
python3 scripts/controller_ota.py --target "$PRIVATE_TARGET" --image "$REVIEWED_NEW_APP"
# Only after attended maintenance approval; this POST also schedules a reboot:
python3 scripts/controller_ota.py --target "$PRIVATE_TARGET" --image "$REVIEWED_NEW_APP" \
  --journal "$NEW_PRIVATE_JOURNAL" --apply --maintenance-confirmed \
  --bare-board-confirmed --attended-reboot-confirmed
```

The uploader freezes image bytes in memory, validates image integrity before any
network request, disables proxies/redirects, supplies BOTH mandatory integrity and
server consistency headers, and acquires the cooperative maintenance lock. It
journals intent before its single POST. Failure, a stale fence or an ambiguous
reply never causes upload replay, implicit rebase, unfenced fallback, USB reset,
arming or settings restoration. A lost transport reply triggers GET-only status
inspection. Rejected/uncertain journals require actual-state inspection before
any further execution. Do not delete/replace a journal just to make a retry run.

Verification requires a new boot, expected full ELF, switched slot, valid/healthy
state, coherent controller metadata, unchanged layout/configuration and restored
Wi-Fi/clock. A confirmed fallback to the old valid image with aborted/invalid
candidate is reported as rollback, not retried. An image can have updated even if
a later verification request fails; inspect the journal and fresh GETs.

## Coverage and remaining limits

Offline tests cover successful fenced upload, lost-success reply without replay,
rejection, no new boot, observed rollback, active/pending-arm/wrong-chip/no-op
refusal, corrupt image before network, changing preflight, altered configuration,
wrong slot/layout/activation, GET failure, clock verification failure, private-LAN
and redirect restrictions, and mandatory POST headers.

Bench-only interrupted staging/rollback coverage is in [GUARDED_OTA.md](GUARDED_OTA.md)
and [OTA_AND_CLOCK.md](OTA_AND_CLOCK.md). It is not a controller physical power-loss
or active-output test. Application health/rollback is not an independent hardware
watchdog, relay contact feedback or a Wi-Fi reachability guarantee.

OTA requires a running reachable native application. It cannot service a chip in
ROM download mode or recover every early crash/network failure. Keep a physical
recovery plan; see [KNOWN_ISSUES.md](KNOWN_ISSUES.md) HW-001 and
[COMMISSIONING.md](COMMISSIONING.md). The successful OTA software reboot does NOT
resolve or resume the deferred physical RET/reset investigation. Incompatible
future storage/partition/contract changes need a separate migration review.

Trusted-LAN/no-auth policy remains unchanged. Fences/digests are consistency and
integrity controls, not authentication. Do not expose the endpoint to the internet.
