# Original ESP32 / Relay_X8 — preparation and attended bring-up, 2026-10-28

**Initial software milestone was compile/offline-test only. Subsequent read-only
inspection and initial native installation are recorded separately below.** Existing
Sunroom/Barn/S3 spare installations are unchanged. User accepted adapters A–I's
six loopback passes as adequate screening for now; cross-adapter, reconnect and
UART-voltage qualification remain unproven. Never infer electrical voltage from
the adapter's separate 3V3 power-output label.

## Subsequent read-only board inspection — 2026-10-28

Jeremy supplied12V, connected UART RX/TX/GND (no adapter power rails), confirmed
relay contacts unloaded, then manually entered downloader with IO0/EN. Passive
115200 startup capture showed normal SPI flash boot/entry but no application
messages; owned capture stopped/TTY closed before protocol use.

No-reset/no-stub ROM identity succeeded: **ESP32-D0WD-V3 rev3.1,40MHz crystal,
4MiB flash**, secure boot/encryption disabled. Thus candidate geometry is now
independently confirmed for this board. The following read used the standard
ESP32 RAM stub/460800baud, streaming full4MiB directly into owner-only encrypted
vault; independent device full-range MD5 plus shelf MD5/SHA256 verified in105.78s.
No raw flash stored on Drallion, no flash/eFuse write, no program/reset-to-app.
Original restoration NOT exercised. Reader closed; CPU left in RAM flasher stub,
so demo stays stopped until an operator reset/power cycle.

Offline original app identifies `esp32-arduino-lib-builder`, Arduino framework
markers and IDF `v3.3.4-286-gb4c075169`. Embedded descriptor date Dec4 2020 is
framework build metadata, NOT proven sketch compile/install date. No MicroPython
or native-project marker found. Source not recovered; stock behavior observed by
operator is sequential relay ON/OFF repetition. Initial search found no contiguous byte/16-bit/32-bit pin array. Subsequent
OFFLINE Xtensa disassembly recovered individual setup/loop calls instead:
GPIO32,33,25,26,27,14,12,13 configured as outputs, all initialized LOW; loop writes
HIGH to all8 in that order, then LOW in the same order, with16 intervening delay
calls taking250. The callee writes ESP32 GPIO W1TS/W1TC registers in both banks,
so these are decoded GPIO writes, not coincidental constants. This agrees with
the matching schematic and our inert starter template. Physical K1..K8 terminal
labels/contact behavior still need unloaded one-channel checks; code alone is
not contact feedback. Detailed private proof: `relay-pin-disassembly-proof.local.json`.

Original slots are1.25MiB at0x10000/0x150000, NOT our new slots/layout; only the
first app slot has an image. Old NVS/OTA/coredump/SPIFFS retained in full backup.
Private pointer: `garden-device-backups/current-relay-x8-uart-inspection.local.json`.
Exact identity, raw captures, security/flash metadata, original image/digests and
checkpoint stay there. No new native image installed, no profile/Wi-Fi/arm write.
Any initial native installation needs a separate exact-artifact plan/new journal;
never replay old S3 or uncertain execution journals.

## Initial native installation — awaiting operator first boot

Jeremy explicitly approved installing/testing our firmware, with relay contacts
unloaded. GPIO sequence above and `profiles/relay_x8_unarmed.json` retain the map.
A historical binary fingerprint differed from the existing local artifact; that
preflight stopped BEFORE remote/serial access. Fresh isolated IDF5.5.1 build:
`build-esp32-relay-x8-install`, controller contract, original ESP32, no PSRAM,
4MiB/DIO40MHz, rollback, diagnostics/fault injection excluded. Audited app:
964,528bytes, SHA256 `be3268590b7bd2fd307763326e675cffd5aae7e52df0f4732df1d8f3561e0869`,
ELF `e7010e3873bf08066b16194862e4a85fb1e03e4ad284fbb9a945569aefaa9742`.
Frozen bootloader/table/initial OTAdata/app, SDK config and source fingerprints
live under private `native-first-install-current.local.json` in the board vault.

New original-only `scripts/remote_relay_x8_bootstrap.py` independently gates exact
physical host/USB path/no TTY owner/exclusive locks, chip MAC/rev301, security,
4MiB geometry and full ORIGINAL device MD5. It validates hashes/layout/target/
controller contract before serial open. UART115200; both SDK whole-file and
block write attempts set1. Never resets/arms/provisions. 11 fake-SDK/PTY tests,
11 original-target +8 release +25 OTA regressions and compiler guards passed.

Initial115200 CONNECT failed before ANY erase/write: backup left RAM stub at
460800. Separate READ-ONLY inspection at460800 reverified identity/security/
geometry and full original device MD5, changed RAM UART to115200, reverified full
original MD5 again. Distinct fresh execution journal then passed all gates and
ONE erase/write/verify pass at115200; all four independent device artifact MD5s
matched, NVS proven blank. No eFuse writes/reset/arming/provisioning. Port closed;
CPU remains in RAM stub; new app has NOT booted yet. Original verified4MiB backup
untouched; restoration unexercised. Failed connection journal retained, never
replayed. Native profile/Wi-Fi/OTA/heap/physical relay tests still pending.

`scripts/receive_relay_x8_boot.py` + `supervise_relay_x8_boot.py` provide bounded
360s/2MiB, receive-only UART capture to mounted vault for attended EN reset;
reader stops10s after RUNTIME_READY, closes port, emits lifecycle metadata. No TX
or reset pulse. Do not reuse a stale/expired capture or replay execution journals.

## First native boot — self-test fixture defect, correction built (not installed)

Operator pressed EN. Matching IDF5.5.1 image boots from0x20000; Lua, board-I/O,
backend, runtime-lease and OTA-fence tests pass. Profile-edit self-test silently
returned false before its normal print: baseline fixture GPIO1 is intentionally
forbidden on original ESP32 (UART0 TX). `ota_boot_check(false)` aborts; repeated
SW_CPU_RESET/BENCH_FAIL, never RUNTIME_READY/API. GPIO reports disabled; no
profile, credentials or arm command issued. Heap260,044/min194,380bytes in this
pre-runtime boot, not a Wi-Fi/runtime heap qualification. Passive capture ended
and released port; full raw evidence remains vault-only.

Fixed ONLY `profile_edit_selftests()` data: common GPIO18/4 instead of S3 GPIO1/2;
invalid sensor fixtures retain collision/unpaired-I2C/unsupported-driver checks.
Early invalid-baseline failure now prints its cause. Pin allowlists/validation,
self-test gate, arming and OTA checks NOT relaxed. Host suite now compiles REAL
`profile_edit.c` and calls the startup self-test for BOTH targets; host-only
buffered streaming-SHA shim uses real OpenSSL SHA256. Reproduced original failure
on ESP32 while S3 passed, then corrected suite passes both. Existing11 original,
8 release/25 uploader tests and compiler guards pass.

Corrected image rebuilt/audited/frozen separately (NOT installed):964,608bytes,
SHA256 `dcc1b8c89101a511fc0325393b50c62cefe67c3c0c8294d3846f0daa8b551466`.
Private pointer `native-selftest-fix-current.local.json`. Requires attended ROM
entry and a separately gated app-only repair; do not replay the initial full
flash worker/journals or claim successful startup from the offline fix.

## App-only self-test repair installed — awaiting attended EN boot

After Jeremy confirmed manual IO0/EN downloader entry, fresh application-only
worker `scripts/remote_relay_x8_app_repair.py` reverified chip identity/rev301,
security/4MiB geometry, EXACT previous app plus bootloader/table device digests,
blank NVS and blank inactive slot. One115200-baud app write at0x20000, followed
by SDK verification and independent device MD5, succeeded. Bootloader/table,
NVS/inactive slot/OTAdata digests proven unchanged afterward. No whole-chip erase,
eFuse write, reset, arm, Wi-Fi/profile provisioning or automatic application start.
Port closed; CPU left in RAM stub115200; corrected app NOT yet boot-validated.
Original stock backup retained and rehashed locally before this operation.

Ten new fake-SDK/PTY/real-image app-repair tests pass: correct app-only flow,
wrong identity/security/geometry/old artifacts/nonblank NVS, offset/new-image/
same-image rejection, write uncertainty stops with NO replay. SDK whole-file and
block write attempts both1. Real profile-edit/backend/commit host suite passes
both targets. Frozen app964,608bytes/SHA above. Private pointer
`native-app-repair-current.local.json` retains separate plan/events/journal;
old initial-flash and first-boot failure histories remain intact. Receive-only
capture and manual EN are the next step; do not infer health from flash verify.

## Corrected self-test passes hardware; factory loader exposed next defect

Next attended EN boot of app `dcc1b8c...` passes ALL startup self-tests, then
`runtime.c:load_profile` fails `ESP_ERR_INVALID_VERSION`. Empty NVS `load_relays`
fallback still used GPIO1, rejected by original ESP32 profile normalization.
GPIO disabled, no RUNTIME_READY, profile import, Wi-Fi provisioning or activation.
This is a second software-port gap, not evidence of bad wiring/flash/RAM.

Audit found that remaining runtime default; target policy now explicitly declares
`GARDEN_FACTORY_RELAY_PIN`:4 on original ESP32, historical1 on S3. Fallback uses
this value, all current/default/AUTO false; GPIO allowlists and arm gates unchanged.
Expanded host suite extracts REAL load_relays/load_profile/adopt_profile, faking
only NVS/clock/parser/SDK operations, and tests empty settings + null zone startup,
expected target default, no NVS writes/output activation, and FATAL refusal of
corrupt/unknown SAVED profiles. Reproduced ESP32-only failure before correction,
then both targets pass. Profile-edit/backend/commit suites and existing11 original,
8 release/25 uploader/compiler-guard regressions also pass. Other hardcoded GPIO
uses in main sources audited; backend negative-test pin mutations remain deliberate.

New corrected image built/frozen, NOT installed:964,640bytes SHA256
`013903cd1778aa7b7dd42c8efdd004ddccec9dec4241c48cda6a2427b25afa3e`.
Private `native-factory-fix-current.local.json`; prior failed images/logs retained.
IMPORTANT: runtime now got far enough to open NVS namespaces and commit schema1.
NVS should no longer be assumed blank. Next repair must first preserve/inspect
actual NVS and verify absence of activation/profile/credentials, then exact-digest
fence and preserve it; never replay/relax the previous blank-NVS repair blindly.
Capture is bounded/finished; board still repeats startup failure until operator
IO0/EN downloader entry. Original recovery image unchanged; no other board touched.

## Factory-default repair installed; NVS preserved and independently reviewed

Jeremy reentered ROM downloader. No-reset read backed up full24KiB NVS into
vault and independently verified device MD5/local SHA256. Strict offline review
found exactly three records: bench/clock namespaces and bench uint32 schema1.
No activation/profile/credentials. New `relay_x8_inert_nvs.py` accepts ONLY all-FF
or this exact inert record set, verifies page/entry CRCs/version/bitmap/padding,
and rejects erased history, variable values, unknown namespace/keys/types/data.
12 parser regressions pass. App-repair worker's original blank-NVS gate remains
the default. New explicit reviewed-schema path independently rereads/decodes NVS
on DEVICE HOST, requires exact local-review MD5/SHA/record summary equality,
then proves all NVS bytes unchanged after the app write. A boolean flag alone
cannot bypass this; three new SDK/PTY regressions cover success, stale fence and
unsafe records, bringing repair tests to13. Real blank-NVS loader tests both chips
still pass. Private backup pointer `nvs-inspection-current.local.json`.

A fresh, distinct app-only execution passed exact current bootloader/table/app,
chip/revision/security/geometry, strict NVS and blank-inactive-slot gates. Wrote
ONLY corrected964,640byte app at0x20000, SHA above; SDK verify plus independent
device MD5 pass. Bootloader/table/NVS/OTAdata/inactive-slot digests unchanged.
No whole-chip erase/eFuse write/reset/arming/provisioning, serial closed. CPU left
in RAM stub115200; need operator EN with capture BEFORE claiming healthy startup.
Current private `native-app-repair-current.local.json` now points to this newest
factory-app repair; its preflight retains the previous repair link. Failed images,
all prior execution/capture journals and stock recovery backup preserved.

## Healthy hardware boot and unarmed UART/memory tests passed

Next EN boot of `013903cd...` reaches BENCH_PASS and RUNTIME_READY. Bounded
receive-only capture finishes/TTY closes normally, no abort/failure/reboot loop.
GET-only UART inspector independently verifies expected chip ID/ELF, ESP32 target,
healthy/valid ota_0, both1.5MiB slot metadata, controller contract, active watchdog
with timeout0/fault injection OFF, GPIO inactive and saved-layout arm false. Factory
profile is one GPIO4, no Wi-Fi credentials. Coherent config/edit/fence checks pass.
Exact captures/snapshot are private under newest app-repair release.

New `scripts/remote_relay_x8_memory_test.py` uses exclusive physical adapter guard,
exact device/boot/ELF/healthy/unarmed checks before and after every POST, fresh
initial edit revision and ONCE-only mutations. Eight Lua cases pass (true/false/nil,
syntax/runaway/sandbox/result/length rejection), valid Relay_X8 profile validates,
UART pin1 and duplicate GPIO validation rejected without import. One inert8-channel
profile import succeeds: hostname relay-x8-bench, pins32/33/25/26/27/14/12/13,
all current/default/AUTO/defaultAUTO OFF, active-high, rules return nil, sensors
all-1, manual/unconfirmed clock. Still no activation/credentials.

All8 logical ON/OFF pairs pass independently while GPIO stays INACTIVE. K1 AUTO
return true evaluates; manual OFF disables current AUTO and stays OFF despite that
rule. Fenced patch restores return nil/AUTO false. Final canonical profile EXACTLY
matches inert template. No physical-coil/contact test implied. Watchdog timeout0,
healthy/valid same boot, all GPIO inactive/unarmed; UART closed. End free heap
139,084bytes/min123,780 after runtime initialization + tests; this is not a long
soak or qualified deadline/stack/OTA test. No Wi-Fi provisioned or reboot issued.

Saved hostname differs from still-active factory hostname; restart_required true
is EXPECTED, not an OTA-ready state. Next operator EN will verify profile retention,
all-OFF startup and unique active hostname. Private release pointer
`native-app-repair-current.local.json` contains `uart-readonly-current.local.json`
and `memory-tests-current.local.json`, with frozen worker, execution events and
snapshots. Never replay those mutation journals.

## Reboot retention and repeated validation passed

Another operator EN boot passes all self-tests/RUNTIME_READY. Fresh UART GET-only
inspection proves DIFFERENT boot ID, same audited ESP32 ELF, healthy/valid state,
active unique hostname relay-x8-bench and restart_required false. Saved profile
EXACTLY equals inert8-channel template: all current/default/AUTO/defaultAUTO OFF,
all return nil, no sensors, manual/unconfirmed clock. GPIO inactive, saved-layout
arm false, no credentials. Five samples0/2/5/10/15s confirm same healthy boot,
watchdog timeout0, inactive/unarmed. End free heap138,620/min121,564bytes.

Separate bounded UART session warms10 validations then evaluates return nil200
more times in8.60s: free heap138,620 ->138,620bytes, profile/edit revision unchanged,
same device/boot/ELF/healthy watchdog and unarmed state before/after. Validation
POSTs only, no persistence mutation/arming/reset/provisioning; serial closed.
Private newest release pointers `retention-check-current.local.json` and
`heap-validation-current.local.json` retain results. This is NOT a long soak,
physical contact test or Wi-Fi/OTA/deadline qualification. Next: select approved
2.4GHz bench network before private provisioning; then Wi-Fi/OTA and separately
attended unloaded relay activation/correspondence testing. No Sunroom/Barn changes.

## Wi-Fi provisioning and five-minute/two-host LAN check passed

Jeremy selected the existing common household Wi-Fi. Matching saved credential
was read privately from approved vault recovery config; only SSH stdin/RAM carried
password to Drallion. No password in argv/logs/new plan/public staging; raw config
not copied, no production-controller settings imported. New original-target helper
`scripts/remote_relay_x8_wifi_provision.py` requires exact device/boot/ELF/healthy/
valid/unarmed/coherent state, expected profile/revision, and provisioned=false before
ONE provisioning request. Stops on ambiguity, no credential replay. Nine offline
fake-UART/HTTP regressions pass, including lost/rejected reply, existing credentials,
identity mismatch, LAN failure, nonprivate IP and redirect refusal. After ACK,
password removed from worker config; this is lifetime minimization, not secure RAM
erasure. Only provision is mutable; subsequent polling is GET-only/no proxies/
redirects. UART closes before LAN observation. No resets/profile edits/arming.

Association/DHCP observed7.99s after one request. Eight Drallion LAN samples at
0/15/30/60/120/180/240/300s (300.6s elapsed) all prove SAME boot/ELF/healthy-valid
controller, unchanged inert8-channel profile, GPIO inactive/unarmed. Zero disconnects,
one BSSID throughout, channel1, normal modem power-save mode1, RSSI-38..-44dBm.
End free heap134,684/min120,956bytes. No router configuration/capture or AP pinning.
Independent shelf GETs also verify expected chip/ELF/boot, profile, healthy watchdog,
connection/disconnect0 and unarmed state. Shelf mDNS resolution did NOT confirm the
expected IP; literal-IP HTTP works from BOTH hosts. Do not diagnose firmware mDNS
failure solely from this resolver result or advertise .local reachability as proven.

Private newest release `wifi-provision-current.local.json` retains sanitized plan,
one-shot execution events and independent shelf snapshot; `target.local.json` holds
new device's LAN target (not production Sunroom/Barn). Credentials now persisted
ON THIS BOARD, so do not replay provisioning or use blank/inert-NVS repair workers.
Wi-Fi reboot retention/long soak/OTA and physical GPIO/contact tests still pending.
Five minutes is a short bench result, not Sunroom diagnosis or production qualification.

## Guarded original-ESP32 OTA/reboot and Wi-Fi retention passed

Jeremy approved one guarded unarmed OTA/reboot test. Fresh same-source controller
build `build-esp32-relay-x8-ota-check`; assigned SDK settings identical to installed
factory-fixed build. New app964,640bytes SHA256
`e3cfe5355efd08d7a5b6a02a4a6e2b5c8ca850a17f89f99165cc92b9b5d4bba9`, ELF
`180967eed3428e85691a4c4c046e6399b6943277499d306892868287e95a557d`.
Original-target release/parser/uploader and both-target actual loader/profile/
backend/commit regressions plus compiler guards pass. Frozen app/ELF/SDK and source
fingerprints retained privately. GET-only preflight passed; exactly ONE guarded
POST (explicit esp32, isolated-unarmed/remote-reboot policy, reviewed12V supply and
no connected equipment) switches ota_0 -> ota_1. New expected ELF/boot reaches
healthy/valid; preserved layout/profile/unique hostname/manual-unconfirmed clock,
all8 OFF/AUTO/defaults false, GPIO inactive/unarmed, watchdog0, Wi-Fi credentials
retained/reconnected and disconnect0. No UART/USB open/reset/arm/settings restore.

Four shelf GET checks0/10/30/60s (60.6s elapsed) plus independent Drallion GETs
confirm SAME new healthy/valid boot/ELF/ota_1, unchanged all-OFF profile, unarmed
and zero disconnects. Free heap134,132/min119,300bytes. This also verifies Wi-Fi
credential retention across this software reboot, not a cold-power-cycle result.
Private `native-ota-test-current.local.json` is NOW current image provenance;
`native-app-repair-current.local.json` and its plan image remain historical. Do
not feed historical image expectations into new provision/repair/inspection jobs.
No forced rollback, interrupted OTA/power-cut, physical activation/contact test,
clock-network/stack/deadline qualification or production deployment performed.
See CONTROLLER_OTA.md. Original stock backup preserved; no commits/publication or
Sunroom/Barn changes. Next physical testing requires attended confirmation and
normal exact-device/layout/boot USB arming, not a firmware bypass of safety gates.

## Attended unloaded activation prepared — WAITING FOR OPERATOR EN

Jeremy confirmed all relay contact terminals empty and explicitly authorized
watching LEDs/listening for unloaded coil tests. Before any activation, ONE fenced
profile patch selects network clock and existing confirmed America/Los_Angeles;
all other profile fields unchanged, all8 current/default/AUTO/defaultAUTO OFF,
active-high, `return nil`, sensors disabled/-1. Synchronized/zone-confirmed valid
clock checked within15s of host UTC. Still inactive/unarmed during clock setup.

New `remote_relay_x8_arm.py` (separate from Barn/S3 helper) has8 fake-UART safety
regressions including wrong identity, pending arm, stale revision, bad clock,
non-OFF defaults/absent operator approval and lost reply without replay. Requires
exact original target/image/boot/device/revision/layout/profile/map/clock plus two
stable coherent snapshots, original adapter topology/TTY ownership/exclusive locks,
no boot/fence/persistence/cleanup/watchdog anomaly, explicit disconnected-load/
operator authorization. One USB `io_arm` request with exact bound phrase/boot/layout
acknowledged; independent USB readback confirms saved arm true but GPIO STILL FALSE
on same healthy boot, unchanged all-OFF profile. No reset or relay-control command.
Port closed. Private `unloaded-relay-activation-current.local.json` retains clock
patch, frozen worker/plan and one-shot arming evidence. Earlier snapshots now stale.

CURRENT ACTION: operator normal EN reset with IO0 released. First verify fresh
healthy/valid boot, same ELF/profile/clock and GPIO active with ALL8 physically OFF,
then test K1 with attended feedback before other channels. Do not OTA while arm
pending, replay `io_arm`, or treat saved arm as already-active GPIO. No coil ON,
LED/click correspondence, contact continuity or reboot-active result yet observed.
If an unexpected relay LED/click occurs during reboot, stop and report rather than
proceeding with channel commands. This is unloaded bench activation, NOT production
Sunroom deployment; contact safety/reset transients/strap/power remain unqualified.

## Unloaded K1..K8 LED/click tests passed — NOT production-ready

Jeremy normal EN reset with IO0 released: all relay LEDs remained OFF. GET checks
prove fresh expected healthy/valid ota_1 ELF, same bound layout/profile, synchronized
network clock, GPIO active/armed, all8 current/default/AUTO OFF. One attended K1
ON/~3s/OFF then K2 ON/~3s/OFF; Jeremy independently confirmed each corresponding LED
and ON/OFF clicks only. He then explicitly requested remaining channels sequentially
~1s each while watching. K3..K8 each ONE ON/ONE OFF with ~1s hold, all-OFF gap and
full state/identity/boot/layout/profile guards before/after transitions. No retries,
other-channel ON overlap, reset/USB open or profile/default/AUTO changes. Each
successful response acknowledges outputs_applied; all-OFF readback follows every
OFF. Authorized distinct OFF cleanup is not replay of a possibly uncertain ON;
any ambiguity stops the sequence. No ambiguous operation occurred here.

Jeremy confirms remaining channels appeared to operate as expected. Fresh final
GET confirms SAME healthy boot/ELF, active/armed GPIO, all8 current/default/AUTO OFF.
Private activation directory retains per-channel one-shot journals, sequence,
operator feedback and final `all-eight-led-click-pass.local.json`. This establishes
coil/LED correspondence and active-high command behavior, NOT electrical NO/NC
contact continuity, load rating suitability, safe reset transients or cold-start
strap behavior. GPIO12/K7 high-level reset/strap interaction remains unqualified.

Controller is STILL ARMED on an inert bench profile (`relay-x8-bench`, K labels,
`return nil`, all AUTO/defaults OFF, sensors disabled). Do not mistake it for a
production Sunroom configuration. Before equipment hookup/cutover: intended12V
supply cold-start/reset checks with UART logic/backfeed qualification, isolated
NO/NC/common contact check, reviewed safe Sunroom function/rule/default mapping,
wall-switch input plan and Garden identity/endpoint cutover. Do not copy old
external-module inversion or hazardous startup ON/AUTO settings; S3-only spare
pin proposals are not an original-ESP32 wall-switch assignment. No live-load,
original-contact-recovery, forced rollback/power-cut or production test performed.

## Second Relay_X8 — healthy/unarmed; unique hostname saved, awaiting EN

Jeremy connected a SECOND same-type board to the same Drallion adapter, confirmed
12V/controller-only supply, empty relay terminals/adapter power pins disconnected,
and manually entered ROM. Separate private root pointer
`current-relay-x8-second.local.json`; NEVER overwrite first board's pointer/identity/
original backup or live Barn. ROM proves distinct ESP32 rev3.1/40MHz/4MiB, security
OFF. Initial read-only size probe stopped BEFORE any flash write: missing ESP32 ROM
SPI attach. Worker now mirrors SDK no-stub RAM peripheral setup, requires default
eFuse SPI pads, then detects geometry (no assumed4MiB fallback). Nine fake-SDK
backup tests cover attach requirement, changed/excluded identity, geometry, short
read/MD5 failures and approval. No flash/eFuse writes/reset in this backup helper.

Full original4MiB streamed directly to vault110.41s, full device MD5 matches shelf
MD5/SHA256. RAM UART restored115200 and identity/full MD5 rechecked before close,
avoiding first-board historical stub-baud failure. Fresh exact-new-MAC/original-MD5/
security/geometry/artifact-fenced bootstrap (11 regressions pass), one whole-chip
erase/write/verify116.3s. Same known-good first-board OTA image installed:
964,640bytes SHA `e3cfe5355efd08d7a5b6a02a4a6e2b5c8ca850a17f89f99165cc92b9b5d4bba9`,
ELF `180967eed3428e85691a4c4c046e6399b6943277499d306892868287e95a557d`, original
boot/table/OTAdata offsets and1.5MiB slots. Four device artifact digests match,
NVS/inactive app blank before first boot, no reset/eFuse write/arm/provision.

After Jeremy normal EN, GET-only UART proves exact new device/ELF healthy-valid
ota_0, factory GPIO4 memory-only profile/all OFF, no credentials/GPIO activation.
Bounded receive-only capture expired with ZERO bytes before that EN; no startup
selftest UART line claimed. Running API health/validity is separately verified.
Memory worker now permits ONLY explicitly reviewed bench/spare names (7 profile
gate regressions); default first-board behavior retained, production names refused.
One inert import and8 Lua/8 logical ON-OFF/auto-manual tests pass, GPIO inactive
throughout. Final exact profile `relay-x8-spare`, same8 K map, all current/default/
AUTO/defaultAUTO OFF, active-high/nil rules, sensors disabled/-1, manual/null clock.
No physical coil commands. Unique hostname is SAVED but pending normal EN to become
active; UART closed, no capture running. Wi-Fi and second-board OTA NOT done yet.

Next: operator EN (IO0 released), verify retained profile/active unique hostname/
healthy unarmed boot, then one private Wi-Fi provision/five-minute LAN check and
separate guarded OTA. Do not reuse first-board arming or clone NVS. Future Barn
replacement needs reviewed mapping: this board8 channels versus current Barn9;
not a drop-in migration or authorization to disturb the active lights controller.

## Second board Wi-Fi and guarded OTA passed — remains UNARMED

After another operator EN, GET-only UART confirms fresh healthy/valid original
ESP32 boot, retained exact8-channel inert profile, active unique hostname
`relay-x8-spare`/no pending restart, GPIO inactive/unarmed, no Wi-Fi credentials.
One private existing-network provision (9 offline provisioning regressions pass),
no resets/arm/profile edits or replay. Credential only SSH stdin/RAM, never argv,
public staging or saved plan/log. DHCP observed6.75s; eight LAN samples over300.4s,
zero disconnects throughout, RSSI-37..-47dBm. UART released before LAN observation.
Saved target uses independently verified SECOND device ID and explicit esp32.

Fresh isolated `build-esp32-relay-x8-second-ota-check` uses identical firmware source
and assigned SDK settings; app964,640bytes SHA256
`f287e1db294a9673f58bac33d7c7b4d320b272dfbbb54315fb48777b3eaea491`, ELF
`a367dd594f901b6cd98caf2e5f5fd9e68415238e306542bb856b035a2365c1f5`.
8 release/25 uploader/11 original-target regressions and compiler guards pass.
Frozen artifacts/source fingerprints and fresh exact-device/boot/profile preflight
retained privately. Exactly ONE fenced OTA POST succeeds; ota_0 -> ota_1, new
expected ELF/boot healthy/valid. Configuration/defaults/hostname/manual-null clock
preserved, Wi-Fi credentials retained/reconnected, watchdog0, GPIO inactive and
arm false. No USB/reset command/physical reset/arming/settings restore during OTA.

IMPORTANT startup caveat: new-boot trace has initial reason7
(CLASS3_FRAME_FROM_NONASSOC_STA) at1968ms, BEFORE first association2570ms and
DHCP4160ms. Counter already1 in OTA-confirmed snapshot. First post-OTA GET check
stopped on overly strict zero-counter assertion; evidence retained, no mutation
or upload/provision retry. Diagnostics establish this as initial-join retry, not
an observed later drop. Cause/AP attribution unknown; NOT old Sunroom reason34 or
proof of a controller/AP defect. Four subsequent shelf GET samples0/10/30/60s
(60.4s) and independent Drallion GETs confirm SAME healthy ota_1 boot, AP/profile,
unarmed/all8 OFF and no additional disconnects (counter remains1). End free heap
134,788/min119,260bytes. Pre-OTA five-minute zero-drop result is distinct from this
recovered startup attempt; do not report post-OTA counter0 or a full long soak.

Private second board `native-ota-release/execution.local.json` and checkpoint are
CURRENT image/boot provenance; its initial-flash plan is historical. All original
recovery data, stopped-probe/assertion evidence, and frozen releases retained.
Normal Wi-Fi OTA goal complete, UART closed/no receiver; leave board unarmed.
Physical coils/contacts/cold-start/reset/forced-rollback/long-term reliability and
reviewed8-versus9-channel Barn migration still pending. Live Barn and first board
not changed; no production profile import/Garden publication/commits.

## Sunroom loads connected: LIVE mapping confirmed K2/K3, all OFF

Operator wired loads (except GPIO18 wall switch) and reported responsibility for
isolated terminal identification. No independent contact/rating/cold-start or
wiring qualification claimed. Historical UNLOADED approvals are no longer current.
K1 was held ON for operator meter work; subsequent LAN GET timeout occurred BEFORE
any OFF POST, and UART fallback stopped before opening because adapter unplugged.
Later identity-verified two-host LAN GETs found ALL8 OFF; no delayed OFF was replayed.

Backup array's fifth entry Outdoor lights/oldS3GPIO40 suggested K5, but live K5
ON test did NOT light outdoors. Explicit user-authorized K5 OFF/K1 short test also
failed to identify outdoors. User explicitly authorized remaining live channels
one at a time while watching. K2 then K3 each ON/~3s/OFF, all-OFF gaps, stable exact
identity/ELF/boot/layout/profile guards and hardware-write acknowledgments. Operator
immediately identifies K2 as Sunroom lights (second from bottom in their view), K3
as Outdoor lights (third from bottom). Therefore CONFIRMED LIVE MAP:

- **K2 / GPIO33 = Sunroom lights** (oldS3 function GPIO41).
- **K3 / GPIO25 = Outdoor lights** (oldS3 function GPIO40).

Old profile ARRAY ORDER DOES NOT establish replacement terminal/load order.
Do not use earlier suggested K4/K5 light assignments or infer remaining functions.
First-board private `sunroom-confirmed-load-map.local.json` records observations;
firmware labels are STILL K1..K8, no rules/inversion/defaults imported or changed.

IMPORTANT interrupt evidence: user interrupted tool after reporting results;
sequence had advanced to K4 ON, and process exit did NOT execute its OFF finally.
Fresh private journal/maintenance-lock inspection proved worker gone, K4 ON with
no OFF intent. New identity/boot/profile-gated cleanup sent ONE K4 OFF, readback
verifies ALL8 OFF, healthy unchanged boot. No K6/K7/K8 live commands executed.
Never assume Python finally or a tool abort made hardware safe. Retain interrupted
journal and distinct cleanup; do not resume/replay sequence. All AUTO/boot defaults
remain OFF, GPIO stays armed, switch/sensors remain unconfigured. Other live loads
unidentified; operate only requested known lights pending further commissioning.

## Confirmed lights renamed; GPIO18 switch wired but NOT configured

User approved confirmed light labels and reports isolated switch wired G18->switch
->GND, no photo sensor. Two once-only boot/revision-fenced live label patches:
GPIO33/K2 becomes `Sunroom lights`, GPIO25/K3 becomes `Outdoor lights`. Readback
exact desired profile, same healthy boot and unchanged armed layout, all8 values/
AUTO/defaults OFF; no rules/input/polarity edits. Current reviewed profile now at
first-board `current-reviewed-profile.local.json`; activation-plan K labels are
historical and MUST NOT be reused as live control labels. Only these2 functions
physically identified; other channels remain unknown.

Current `sensor_pins.light_switch` is STILL -1. Board driver supports GPIO18
internal pull-up, closed-to-GND=true,40ms debounce; acquisition of switches is
independent of optional environmental sensors. But `io_live_settings_compatible`
locks input resource changes while active. No attempt to bypass, OTA around arm
binding or claim a pull-up/input test happened. Adding GPIO18 requires isolated
USB disarm/reconfigure/rearm with attended resets. UART adapter last reported
unplugged, so this is pending, not a live-settings-only operation. Switch physical
pad/electrical isolation relies on operator report, not independent measurement.

## Live input OTA deployed — GPIO18 enabled without USB, toggle pending

2026-10-29: Jeremy approved simplifying routine input edits rather than repeating
USB disarm/reconfigure/re-arm. Implemented/tested bounded live switch enable/remap/
remove with all old/new current/AUTO/boot defaults OFF, unchanged relay ownership/
polarity/clock/environmental sensor settings, input-only GPIO staging and rollback,
no invented edges, existing arm binding coherently updated. Original ESP32 straps
cannot be newly selected remotely. Initial USB hardware enablement unchanged.
See LIVE_SWITCH_INPUTS.md for failure semantics, tests and explicit all-OFF OTA.

One attached-load, explicitly approved all-OFF OTA switches first board ota_1 ->
ota_0:965,808byte SHA `c92871627cbda59b522f6546575ef6a26056d3111029411c08c47384101e3dfb`,
ELF `e481598cdad857b38b35afc586b1b3e1ff96b2fb0a0f42cfbd7ea88c15d70997`, new
healthy/valid boot, all8 current/AUTO/defaults OFF, active/armed GPIO, Wi-Fi/profile/
confirmed light names retained. No UART, no physical isolation/lights-only claim.
Then one fenced live input patch light_switch -1->18 succeeds SAME BOOT, active/
armed binding retained, all8 OFF. Four non-simulated input samples false/open;
operator toggle and connection to light automation still pending. No relay rules/
AUTO changed. `live-switch-release-current.local.json` and current reviewed profile
are NOW image/layout provenance; old arm/OTA plans are historical. Barn/second
board unchanged, no Garden publication/commits, recovery media retained.

## Selectable builds, existing S3 retained

```sh
# Original ESP32, memory-only bench contract native-profile1
bash scripts/build.sh --target esp32

# Original ESP32, controller contract relay-profile1, still UNARMED
bash scripts/build.sh --target esp32 --controller

# Existing S3 remains default; legacy explicit IDF options still work
bash scripts/build.sh
bash scripts/build.sh --target esp32s3 --controller -B build-s3-target-check
```

New convenience defaults use separate directories and per-directory sdkconfig:
`build` (S3 bench), `build-esp32` (ESP32 bench),
`build-esp32s3-controller` and `build-esp32-controller` (controller families).
Explicit `-B`/`-DSDKCONFIG`/`-DSDKCONFIG_DEFAULTS` still supported; do not combine
`--controller` with explicit defaults. Never point target experiments at frozen
production build directories or run `set-target` there. Only ESP32/S3 supported.
Controller defaults do NOT save an arm record or authorize physical operations.

`main/target_board.h` centralizes target name, ESP image chip ID and GPIO policy.
The S3 allowlist is IDENTICAL to the previous implementation; so is its layout
hash encoding/arming record, profile schema and existing partition table. The
original ESP32 gets its own allowlist, not a union of both architectures.

## Original ESP32 build candidate

`sdkconfig.esp32.defaults`: candidate4MiB, DIO/40MHz, internal RAM (no PSRAM),
UART0 console/setup115200, rollback enabled. **Actual flash size/security are
unknown until physical ROM identification** for any new board. This particular
board's4MiB/no-security geometry was independently identified above. A shield
marking/photo alone is not a ROM geometry check; never flash a guessed layout.

`partitions.esp32.csv` retains NVS0x9000/0x6000, otadata0xf000/0x2000 and
PHY0x11000/0x1000. Apps: ota_0 at0x20000 and ota_1 at0x1a0000, each0x180000
(1.5MiB). Table ends0x320000 within4MiB, leaving896KiB unallocated. Current
controller app is964,528bytes (~942KiB), leaving608,336bytes (~594KiB,38.7%)
per slot: no feature reduction needed for FLASH capacity. OTA transfers only the
app, not the full4MiB recovery dump. Runtime heap/stack/deadline/stability still
need hardware qualification. S3 still has two3MiB slots/16MiB build.
**ESP32 bootloader flash offset is0x1000, not S3's0x0.** Use generated artifacts
for the selected target only, never splice S3 bootstrap files into this layout.

UART0 JSON setup/replies, private credential provisioning, profile validation/
import, USB-attended chip/boot/layout-bound arm/disarm, HTTP APIs, Lua rules,
clock, progress watchdog and guarded OTA share the implementation. Original
ESP32 has no native USB peripheral: the S3 secondary-console/FIFO code is already
compile-guarded and is absent from the ESP32 build. A UART adapter is the physical
maintenance link. RX/TX/GND adapters without wired DTR/RTS cannot perform automatic
BOOT/EN reset; do NOT assume `Device.reset()` or esptool auto-reset worked. Operator
buttons/power cycling need their own attended sequence and boot verification.

The old physical GPIO4/5 + I2C1/2 spare diagnostic is S3-only (Kconfig dependency
and C compile guard); it must not touch original ESP32 UART0. Pure boot backend
selftests use GPIO18 instead of GPIO6 on ESP32: GPIO6 belongs to SPI flash there.
Real backend/profile/commit fault tests now compile and execute for BOTH policies.

## Relay_X8 board policy and starter profile

Photos identify `ESP32_Relay_X8 (303E32DC810)` / ESP32-WROOM-32E. Matching reference:
https://www.pollin.de/media/8c/9e/bd/1773061638/D811724-D.pdf?ts=1773061638

Reference K1..K8 GPIOs: **32,33,25,26,27,14,12,13**, active-HIGH NPN drivers.
Reference schematic is not a measurement of this particular assembly. Verify
channel correspondence, polarity, reset/cold-boot behavior with NO loads attached.
Relay contact markings are not certification of the whole PCB/enclosure/load.

`profiles/relay_x8_unarmed.json` is a credential-free, OPTIONAL import candidate:
eight generic K labels; logical/default values OFF; current/startup AUTO OFF;
`return nil` rules; all sensor pins disabled; manual/unconfirmed clock. It is NOT
installed automatically and contains NO activation record. Production Sunroom
labels/rules/switch/clock/defaults are not copied, particularly its two ON startup
defaults and mixed inversion. Map those deliberately later; every Relay_X8 driver
is expected active-high (`isInverted:false`), not the old mixed inversion list.

ESP32 policy excludes UART0 GPIO1/3, SPI-flash6..11, input-only34..39, nonexistent
and S3-only pins. GPIO5/12/15 are permitted but are strapping pins; Relay_X8 K7
necessarily uses12. Firmware defaults cannot control ROM/reset levels: confirm
external bias (especially GPIO12 flash-voltage strap), coil/contact behavior and
power stability BEFORE commissioning. Optional sensors remain deferred. No
software guarantee against reset-time relay pulses or physically stuck contacts.

## OTA / release separation

Firmware compares incoming header chip ID against its COMPILED target (ESP32=0,
S3=9), then preserves project/contract/digest/fence/slot/health checks. `/api/config`
and `/api/ota/status` advertise `chip_target`; OTA adds `image_chip_id` and actual
`update_partition_bytes`. Slot-size rejection is device-side before OTA writes.

Host tools default to S3, preserving historical callers. ESP32 requires explicit
`--chip-target esp32`; offline image verification uses its1.5MiB ceiling. Online
preflight requires coherent ESP32 target/chip/actual-slot metadata and rejects
cross-target/oversize images before POST. Only old S3 metadata gets the legacy
fallback. `controller_ota.py` additionally requires the private target JSON to
contain `"chip_target":"esp32"` when selected. Lost responses still lead to GET-
only inspection, never upload replay. Post-update target/slot metadata is checked.

```sh
python3 scripts/controller_release.py --chip-target esp32 \
  build-esp32-controller/garden_native_probe.bin
```

Existing S3 initial-flash/backup/bootstrap/resume workers remain intentionally
S3/16MiB-specific; do NOT weaken/reuse them on the new board. Before first ESP32
write, implement/review an original-ESP32 security/geometry/full-backup workflow,
retain verified original flash in unlocked vault, freeze exact artifacts and an
exclusive fresh execution journal. No automatic restoration or replay.

## Verified / not yet verified

- Actual IDF5.5.1 controller compilation for original ESP32 and S3; correct chip,
  flash settings/offsets and app fits each target's two equal slots.
- Offline checksum/appended SHA/project/contract audit of both actual images.
- Existing8 release +25 uploader regressions; new cross-target/size/metadata,
  original-target success/lost-response/no-replay, real pin-policy, inert starter
  profile, partition and build-argument/config-isolation tests.
- Actual backend/profile/NVS-fault host tests under both target policies;
  compiler controller/fault-injection exclusion checks on both IDF builds.
- Wi-Fi ring/JSON/power-policy/single-AP helper tests retained/passing.

Healthy original-ESP32 boot, UART RPC, unarmed8-channel memory controls, reboot
retention and200-evaluation no-heap-decline check are now verified as above.
Wi-Fi association/DHCP/five-minute stability and two-host literal-IP API access
are verified above, as are one guarded normal OTA/slot switch and Wi-Fi retention
across its software reboot. Runtime stack/deadlines/long soak, forced rollback/
interrupted OTA/power-cut recovery, relay electrical behavior, cold-start/strap/
power and physical activation remain unverified. Logical tests/build success are NOT commissioning.
