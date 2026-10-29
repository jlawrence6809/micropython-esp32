# Relay-first commissioning / recovery review — NOT authorization to flash

**2026-10-26 Barn extension:** explicit user lights-only remote maintenance and
acceptance of live setting output changes supersedes older bare/main-OFF-only
policy for that session. One armed fenced OTA succeeded; live polarity/default
settings and coherent arm rebinding implemented/tested/applied. See
[LIVE_RELAY_SETTINGS.md](LIVE_RELAY_SETTINGS.md) and current BARN_BRINGUP.md.
Overhead startup AUTO now true (later boot test pending); Flood light polarity
flipped (physical confirmation pending). Pin/input/clock remapping still isolated;
future power equipment requires policy review. No Sunroom2 changes or renewed
RET investigation. Initial activation remains USB-only; existing active arm can
be rebound on successful permitted settings edits. Historical sections follow.

**2026-10-16 decision:** Jeremy explicitly deferred the Sunroom2 RET/reset
investigation. [KNOWN_ISSUES.md](KNOWN_ISSUES.md#hw-001--sunroom2-retreset-can-select-rom-download-mode)
records HW-001, evidence, uncertainty and operational consequences. All capture
readers are stopped. The historical "next test" notes below are superseded by
this decision: do not continue hardware experiments unless requested. Deferral
does not authorize GPIO arming, live loads or skip other commissioning gates.

**Subsequent clock setup:** Jeremy confirmed Seattle / `America/Los_Angeles`.
After a normal replug to USB TTL on Drallion, network-only preflight succeeded.
Exactly one fresh boot/revision-guarded narrow profile patch saved that timezone
and `clock_source: network`; read-back verified SNTP synchronization, valid
schedule clock, unchanged eight-relay definitions/defaults/AUTO and other profile
settings, same healthy boot and GPIO inactive/unarmed. `edge_no_catchup` retained.
No serial open, reset, arming or physical output command was issued. Older
"timezone unconfirmed" entries below are historical, not current. The latest
clock change has not been separately reboot-tested; do not resume reset tests
merely to do so while HW-001 remains deferred.

**Barn GPIO ACTIVE, subsequent 2026-10-20:** operator confirmed native USB replug
while equipment main remained OFF. LAN-only verified new healthy valid expected
boot, GPIO active/armed, simulated=false, all nine manual/logical OFF/defaults,
no per-relay/cleanup/watchdog error, stable follow-up reads. LA clock saved and
synchronized after restart. No light-toggle/reset/serial command. Actual contact
polarity/OFF safety/live-load behavior remain untested. Coordinate attended main
power restoration/initial light observation before an overhead-only API test;
other eight remain manual OFF, no AUTO restoration or other live-output tests.

**Earlier Barn USB arm, 2026-10-20:** Jeremy explicitly re-isolated main power OFF,
connected native USB and requested GPIO enable. All nine logical values/defaults
reviewed OFF; only Overhead AUTO/defaultAuto were disabled for a preserved manual
test profile, production snapshot retained privately. One exact USB chip/layout/
boot/confirmation arm command acknowledged and read back. GPIO remains inactive
in post-close LAN checks; activation pending reboot. No reset/output/live-light
command. Next operator native-USB replug with main OFF, then LAN-only real active
mode/fault/default checks before any main-power/live-light step. Saved arm can
activate on USB-induced restart. BARN_BRINGUP.md is current; no blind replay.

**Earlier Barn circuit power / clock, 2026-10-20:** Jeremy removed USB/restored main
power and reported overhead ON. LAN confirms exact healthy native chip/ELF, Wi-Fi,
GPIO inactive/unarmed; `Overhead` pin18 AUTO reports logical OFF. No physical
control/contact safety inferred. One explicitly approved guarded clock-only
patch set LA/network and synchronized valid PDT; all definitions/defaults/AUTO
unchanged, same healthy boot. No light/output/arm command. Clock reboot persistence
and physical commissioning still pending. Old main-OFF maintenance approval is
not applicable now; re-isolate before serial/USB arming review. Never silently
arm the restored production AUTO profile merely to fulfill an overhead API test.

**Earlier Barn native USB continuation, 2026-10-20:** With explicit approval and the same
main-OFF/native-USB-only arrangement, native setup input was added while retaining
UART logging. The RX-fixed app boots healthy/valid; 9-relay import and private
Wi-Fi provision were each acknowledged once, read back, and independently checked
over LAN after USB closed. Native exact-limit/overflow/recovery tests passed on
the same healthy unarmed boot/revision/layout. [NATIVE_USB_SETUP.md](NATIVE_USB_SETUP.md)
is current. A subsequent observed USB reset/new boot preserved profile/Wi-Fi and
activated `barn` hostname; exact USB transition not isolated, cold-power behavior
not proven. Clock confirmation, physical commissioning and Barn OTA remain
unfinished. USB opens remain potential restarts requiring maintenance isolation. All readers closed. Do not replay
the earlier interrupted journals or restore merely because of their missing replies.

**Earlier Barn partial migration, 2026-10-20:** Jeremy identified the separate Barn board
on Drallion, equipment main power OFF / ESP32 USB-only, and approved backup/flash.
Original full flash/device digest and 36 recovered files/9 relay definitions were
verified; native erase/write/all FOUR image digest checks passed, first reset
issued. SSH then dropped and Drallion became unreachable. Native boot/config/
Wi-Fi are UNCONFIRMED; no arm command. Existing remote worker may own TTY/continue;
inspect actual process/device/journals before any further execution, NEVER replay
flash/restore. Keep equipment main power OFF. [BARN_BRINGUP.md](BARN_BRINGUP.md)
is the current checkpoint and next-step authority for that board.

**Subsequent OTA prove-out, 2026-10-16:** Jeremy explicitly approved a Wi-Fi
update while Sunroom2 remained bare on Drallion USB. One fenced upload/HTTP 200
switched ota_0 -> ota_1 and reached the expected new healthy/valid ELF/boot, with
profile/layout/eight relay definitions/defaults/AUTO, Wi-Fi and synchronized LA
clock verified. Three further checks retained the same healthy boot. GPIO stayed
inactive/unarmed; no serial open, RET press or recovery was used. The only firmware
change adds a nonsecret startup summary. [CONTROLLER_OTA.md](CONTROLLER_OTA.md)
details the new UNARMED-only executor and 24 offline tests. HW-001 remains deferred;
active-output OTA and physical commissioning are NOT implied by this result.

Software work and the disconnected spare are authorized. On 2026-10-15 Jeremy
removed Sunroom2 entirely from its circuit and attached it by USB to the shelf
server for migration and backups. Its initial controller image is flash-verified,
and one cold boot passed healthy/unarmed identity checks; repeated USB sessions
remain blocked by adapter/reset behavior (see section 3). This limited approval
does not authorize GPIO arming, reconnecting equipment, Barn changes or live
relay/module/contact tests. Those remain separate attended approval gates.
Actual sensors are optional later; unavailable readings must remain nil.

## 1. Before any live USB access or flash read

- Identify one exact device, physical location, adapter/port, chip ID, board and
  wiring. Do not infer identity from a reused IP, hostname, `/dev/tty*` name or an
  old profile. Opening an adapter or entering a bootloader can itself reset it.
- Agree on a maintenance window and operator. Isolate loads / provide a separate
  safe manual control appropriate to each attached device. Do not assume GPIO OFF,
  input/floating cleanup or a successful command means contacts are open.
- Review module polarity, boot/ROM/reset/strap behavior, supply/grounding, pulls,
  wall/reset switches and brownout risks. GPIO4/5 spare pad tests do not validate
  any live relay module/contact or GPIO48.
- Confirm intended timezone/DST and boot/missed-edge/time-correction policy.
  `edge_no_catchup` is not date-event deduplication; custom current-time-only Lua
  may intentionally catch up. Do not infer timezone from inconsistent old clocks.
- Preserve the API exports/translated profiles and obtain a verified **full flash**
  backup before replacement. API profiles exclude Wi-Fi credentials and are not
  a bootloader/filesystem/NVS backup. Flash reading is itself a reset/maintenance
  operation, not a safe background task.
- Keep raw dumps, Wi-Fi material and exact private manifests in the unlocked
  encrypted private-services vault, restrictive modes, never Git/chat/arguments.
  Verify capacity/hash/read-back and record the original tool/version/flash layout.
  Prepare an exact original-image restoration procedure for the verified board;
  do not improvise erase/restore commands while equipment is connected.

## 2. Offline release review

- Review source changes and artifact provenance. No authentication is present by
  explicit trusted-LAN choice. SHA/project/chip/contract checks are integrity and
  compatibility checks, not a signature or permission boundary.
- Build normal bench and separate `relay-profile1` controller artifacts with no
  physical, pending-boot or runtime-stall diagnostics. Run compile guards and
  software regressions. Never use a diagnostic image on connected equipment.
- `python3 scripts/controller_release.py build-controller/garden_native_probe.bin`
  checks ESP32-S3 header, project/contract, slot size, segment lengths/checksum and
  appended SHA256 offline. It rejects the normal bench image. Record file/ELF
  digests privately with release provenance; this does not prove safe source code.
- Verify Garden native editing on an actual phone before live migration. Old
  clients still replay full arrays; new native editing uses atomic patches.
  Test keyboard/blur validation, serialized autosave/conflict/error messages,
  navigation, manual/AUTO and unavailable sensors against only the spare.
- Publish only after reviewing phone-originated sync changes and the normal Git/
  Hetzner procedure. No new APK is required for these web-only changes. No phone
  publication or real-phone test has occurred during this milestone.

## 3. Disconnected controller bring-up — attended gate

2026-10-15 / 2026-10-16 Sunroom2 checkpoint:

- Full 16 MiB original flash saved in the unlocked encrypted vault, SHA256 recorded
  and independently verified against the device. Offline LittleFS extraction
  recovered 31 files, identity, Wi-Fi material and all eight relay definitions.
  Fresh rules/pins/polarity/defaults match the previously reviewed API export.
- A diagnostic-free `relay-profile1` image and its bootloader/partition/OTA-data
  artifacts were frozen privately, flashed after full erase, and verified twice.
  **No arming command, profile import or Wi-Fi provisioning was issued.**
- After Jeremy unplugged/replugged USB, native runtime checks PASSED: expected
  chip/ELF/contract, healthy valid image, GPIO compiled but inactive, saved layout
  unarmed, no cleanup/fault flags. The next USB session failed before any import
  or credential mutation. ROM DOWNLOAD mode recurred during reset investigation.
- This CH340 TTY had Linux HUPCL enabled. `usb.py` now clears HUPCL on its explicitly
  opened maintenance port (transient termios only, no udev/global policy). Four
  offline flag/error tests pass, but the next cold-boot experiment again passed
  its FIRST GET-only session and FAILED its SECOND. HUPCL clearing is insufficient;
  the adapter/board reset cause remains unproven. DTR and RAM-stub WDT attempts
  likewise did not restore runtime access. No import/credential mutation started.
  Do not repeat reopen tests or reconnect equipment.
- On 2026-10-16 Jeremy clarified a previously reported power cycle had not actually
  occurred; the shelf adapter had remained enumerated since the previous day.
  Following a confirmed reconnect, ONE continuous provisioning session succeeded:
  eight Lua rules validated, canonical profile imported/read back with matching
  layout, private Wi-Fi credentials saved and station connection confirmed. Both
  mutations have separate acknowledgements in the private execution journal.
  Exact expected chip/ELF, healthy valid image, inactive GPIO and unarmed state
  were verified after provisioning. No reset/arming/output command was issued.
- The first post-provision USB-close audit and subsequent network-only cold-boot
  checks failed; a charger/bank-powered check also failed. The adapter was absent
  during the charger test. No mutation was replayed. These failures do not prove
  firmware crash, a specific strap/reset cause or failed credential persistence.
- A later single passive UART session captured a CLEAN `SPI_FAST_FLASH_BOOT`,
  passing startup tests, saved hostname `sunroom2`, saved Wi-Fi present, station
  authentication/association and DHCP. Its IP was unchanged. GET-only network
  checks verified the expected new healthy chip/ELF/layout, all eight persisted
  relay definitions/Lua/defaults, Wi-Fi, active hostname and inactive/unarmed GPIO.
- Controlled passive-monitor shutdown followed by GET-only checks at 2 and 12
  seconds retained the SAME healthy boot. Thus closing UART alone did NOT
  reproduce the outage; do not label that as the established root cause. Logs
  and snapshots remain private. The reader is stopped and serial tools closed.
  Standalone charger startup/repeated USB-open behavior remain unresolved.
- Later on 2026-10-16 Jeremy moved the isolated board to Drallion USB. Explicit
  read-only SSH verified Drallion and the CH340 adapter; shelf adapter was absent.
  WITHOUT opening either UART, the cold-power network audit PASSED: a new healthy
  expected controller boot, persisted eight-relay profile, active hostname and
  inactive/unarmed GPIO. This is a successful no-serial-open cold boot on Drallion,
  not proof of the charger/shelf failure cause.
- Physical RESET/EN on Drallion with UART closed failed the first network probe
  and a further bounded 50-second GET-only recovery window. A passive remote
  standard-library UART reader then opened the adapter and atomically deasserted
  DTR/RTS; a CLEAN SPI boot, startup pass and runtime-ready message were captured,
  followed by successful expected healthy/inactive/unarmed network checks. No
  UART commands or reset pulse were sent. This is correlation with adapter-line
  handling, not an established GPIO/ModemManager root cause. ModemManager was
  active but recent target-port journal mentions were absent; no service changed.
- `capture_uart_remote.py` runs via explicit SSH stdin on Drallion, installs no
  packages/project files, takes exclusive TTY access and streams raw logs directly
  to the encrypted shelf vault. Initially bounded to 600 s / 2 MiB, it now uses
  3600 s / 2 MiB for attended tests because operator replies can arrive after
  the shorter capture expires. Always check lifecycle timestamps. Prior test:
  operator RESET/EN while this SAME reader remained open was CAPTURED: initial
  clean `boot:0x29 (SPI_FAST_FLASH_BOOT)`, startup PASS/runtime-ready; physical
  RESET/EN then `rst:0x1 (POWERON),boot:0x23 (DOWNLOAD(USB/UART0))`, `waiting for
  download`, no second runtime-ready marker, network unreachable. Thus this
  reset failure occurs BEFORE the native application, not in Lua/Wi-Fi startup.
  GPIO0/strap/USB-auto-reset hardware is the next investigation; the exact cause
  is NOT established. The reader has been stopped and UART released. Obtain a
  board/buttons/USB topology photo and inspect boot/reset wiring, rather than
  reflash/replay provisioning. Do not arm/reconnect equipment.
- Photo confirms separate adjacent printed RET/BOOT buttons, a dual-USB-C
  ESP32-S3-N16R8 external-antenna board, cable on CH340/UART side. Jeremy confirms
  pressing RET and reports other cheap boards with apparently reversed labels.
  Treat reversal as plausible, NOT established; identify behavior empirically.
  Precision-RET follow-up found an empty reader that had expired at 18:42:39Z,
  inspected at 19:00:08Z: this cannot establish whether/when the button reset.
  A fresh one-hour capture then recorded the comparison: printed BOOT alone
  added no UART bytes/reset banners; printed RET alone using a nonmetallic probe
  added `rst:0x1 (POWERON),boot:0x21 (DOWNLOAD(USB/UART0))`, waiting for download,
  no application start. These observations fit normal button roles; reversal
  is not supported, accidental finger contact is less likely, and the precise
  boot-selection cause remains unproven. The reader was stopped and port released.
  The single cable was then moved from the UART-side USB-C port to the native
  ESP32 port. Drallion enumerated Espressif 303a:1001 USB JTAG/serial, not CH340.
  With NO native serial open, a full network audit PASSED: expected healthy image,
  all eight persisted relay definitions, Wi-Fi/hostname and inactive/unarmed GPIO.
  RET-only reset on this native port then FAILED the network audit, including
  a bounded 35-second GET-only recovery window; native 303a:1001 remained
  enumerated. No serial interface was opened. Thus native-port cold boot worked
  but the port change did NOT fix reset behavior. Current native-port failure
  mode was not captured: do not assert ROM mode/crash from network failure alone.
  Prior UART-side captures explicitly entered ROM DOWNLOAD. Next obtain actual
  GPIO0/BOOT electrical or equivalent boot-state evidence rather than repeat
  button/port cycles or reflash. Keep only one USB cable connected. Native USB
  logging does not imply UART0-only JSON provisioning/arming RPC support.
  Never rerun provisioning. Timezone remains unconfirmed (`null`, manual clock);
  no physical commissioning has occurred.
- Private execution/recovery journals, artifact copies, original image, extracted
  files and an unconfirmed credential-free native profile are under the vault's
  `garden-device-backups/current-sunroom2-usb` pointer. Never replay a journaled
  erase/write/import after uncertainty. Original-image restoration is prepared,
  but has NOT been executed/tested.

Sunroom2-specific initial-USB helpers are `scripts/backup_usb_flash.py`,
`scripts/extract_legacy_flash.py` (ephemeral littlefs-python; explicit mount,
read-only context, never format) and `scripts/bootstrap_controller.py` (default
prepare-only; explicit attended/disconnected-load acknowledgements plus `--apply`
for one journaled execution). They require private verified recovery material;
these are not generic live-controller/OTA/arming tools. Their UART adapter
opening/reset behavior still requires maintenance approval.
`commission_controller.py` now provides ONE continuous, one-shot initial restore
with expected identity/image/healthy/inactive gates, separately journaled profile
and Wi-Fi mutations, no adapter reopen/reset and a GET-only network audit after
USB close. It deliberately defers hostname activation to an operator restart.
Its initial Sunroom2 profile/Wi-Fi mutations completed and were USB-verified on
2026-10-16. Its post-close network audit failed; do not equate successful USB
provisioning with proven standalone boot or physical safety. A later passive UART
boot capture and network audit DID verify profile/Wi-Fi persistence and hostname
activation. `capture_uart_startup.py` is an explicitly acknowledged, vault-only,
passive reader, bounded to 600 seconds/2 MiB; it sends no commands or resets.
Normal firmware already emits ESP-IDF UART0 boot/Wi-Fi/error logs and startup
checks without needing a host or debug reflash. Raw logs can contain SSIDs and
private identifiers; keep them encrypted, restrict access and sanitize reports.

- Preserve original rollback/recovery media and identify the exact flash tools.
  Inspect firmware contract/role, boot/ELF/chip/layout IDs and fault flags after
  initial flash. A bench image must never become an armed controller.
- Provision Wi-Fi over USB without echoing credentials. Import only a reviewed
  credential-free canonical profile; import cannot enable GPIO. Verify labels,
  order, pins, polarity, current/default AUTO/value, rules, input reservations,
  timezone/source and reboot behavior. Re-read after any uncertain import.
- Confirm optional sensors are disabled/unavailable and relay-only boot/health
  needs neither a connected sensor nor Wi-Fi/NTP availability. Network schedules
  require a confirmed zone and valid guarded clock, not just a healthy boot.
- Review actual startup/default, inversion, module/contact, switch debounce,
  reset, supply/brownout and recovery behavior with isolated/test loads first.
- USB arming uses an exact phrase and independently verified device/boot/layout
  IDs; the device checks the boot nonce under its lock, not only in CLI preflight.
  Even `controller_io.py status` needs its maintenance acknowledgement since
  adapter opening can reset hardware. Arm/disarm affect the next reboot only.
- Do not use OTA as an incidental arm/disarm/hostname-activation reboot. A saved
  armed layout and currently active GPIO must agree before a routine update.
- Only after review: approve one live controller at a time. Keep operator/manual
  fallback available. Record what was actually observed, not just successful API
  returns. No live arming/flash has been authorized by software iteration.

## 4. Native controller OTA reservation / current tool boundary

`controller_release.py IMAGE --host IPV4 --expected-device-id CHIP_ID` performs
only GETs. It checks a healthy valid controller, exact expected chip, coherent I/O,
no cleanup/fault/deferred identity/boot-selection state, a stable boot/revision/
layout/image fence across two snapshots and an actual changed image. It does not
print profile/SSID/labels or raw identity tokens. Bench tools still refuse even
an unarmed controller. Offline/fake tests cover both coherent active/inactive
states and pending arm/disarm rejection. The first disconnected Sunroom2 USB
image write, healthy/unarmed boots and profile/Wi-Fi persistence/hostname
activation through a captured boot and network audit are verified. One subsequent
attended UNARMED controller OTA also passed; see CONTROLLER_OTA.md. Standalone charger/reset/repeated USB-open behavior, physical
commissioning, active-output OTA and controller power-loss/rollback remain
unresolved.

**The audit tool has NO upload/reset/arm path.** Client-only preflight was
insufficient, so the server now provides mandatory controller fences and a
configuration/arming reservation through upload, selection and reboot. It uses
short runtime-lock checks, never a mutex across image receives. Explicit writes
reject while reserved; automation remains enabled. See GUARDED_OTA.md for the
protocol, pure mandatory-controller tests, actual spare staging/abort/USB-gate
coverage and successful fenced bench update. Do not bypass review with curl.

The separate UNARMED-only executor is implemented and one actual update passed;
see CONTROLLER_OTA.md. The following gates still apply before extending execution
to active outputs or claiming broader recovery coverage:

1. Review the implemented fence/reservation and failure/reboot windows. Test
   controller-specific behavior with disconnected hardware only after approval;
   bench OTA execution and one disconnected UNARMED Sunroom2 OTA are verified;
   active-output execution and completed physical commissioning are not.
2. Extend controller commissioning/update execution tooling to active-output
   maintenance only after review, retaining explicit attended-reboot acknowledgement,
   independently verified identities/artifact and no automatic mutation retries. Missing/unsupported
   guarded-OTA metadata must fail closed; do not fall back to bench tools.
3. Extend interrupted/failed storage/power and rollback/recovery coverage. A same-
   image audit is refused rather than using OTA as a gratuitous equipment reset.
   Resolve pending arm/disarm/hostname changes separately. Never automatically
   replay an uncertain upload/import or silently rebase a stale token.
4. Verify the new healthy valid ELF/boot/slot, canonical configuration, layout/
   arming/active mode and truthful output errors afterward. Runtime values can
   legitimately differ from defaults after an immediate rule; not contact feedback.
5. Maintain the full-backup and actual phone/electrical/operator gates above.
   No actual controller update/flash/arming is authorized by software iteration.

## 5. Recovery is not always rollback

- Pending boot failing local validation: inactive-slot rollback is implemented and
  tested on the bare spare. Preserve a known compatible slot/original full backup.
- Valid image with a later task stall: the application progress monitor restarts
  the **same** valid image, not an older image against newer settings. Boot defaults
  run again; this can cycle loads and requires an equipment-level safety review.
- The progress monitor is not an independent hardware watchdog and cannot act if
  scheduler/monitor execution itself stops. Heartbeats do not prove network
  reachability, correct rules, healthy wiring or safe contacts.
- Unexpected reset, unreachable network, cleanup failure or uncertain mutation:
  stop repeating actions; inspect identity/boot/image/profile/arming and physical
  state with the operator. USB inspection itself can reset. Power-cut durability,
  full recovery on actual modules and independent physical safety remain unproven.
