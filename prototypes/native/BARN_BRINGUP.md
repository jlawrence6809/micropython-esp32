# Barn migration and commissioning — updated 2026-10-26

Initial backup/migration approval was main-OFF/USB-only and did NOT authorize
GPIO. Later explicit GPIO and overhead-light approvals/states are recorded below;
do not treat historical isolation approval as current isolation. This is Barn,
NOT Sunroom2. Current equipment main power is ON; GPIO is active.

## Current: lights-only armed OTA + live settings verified — 2026-10-26

Jeremy returned after several days, reported ONLY lights/no power equipment,
accepted relay changes during settings edits and requested remote OTA. One fenced
upload confirmed expected new healthy/valid ota_1 boot, active/armed GPIO, unchanged
config/layout, connected Wi-Fi and synchronized clock; no USB/reset intervention.
New image and policy/test details: [LIVE_RELAY_SETTINGS.md](LIVE_RELAY_SETTINGS.md).

Separate one-shot commands then restored pre-update Overhead ON within its
schedule window, set current/startup AUTO true, and flipped Flood light(pin4)
isInverted true->false while preserving label/logical value. Live edits now
rebind the existing coherent active arm without disarming/rebooting; other seven
rows and 08:00/20:00 Seattle/wall-switch rule unchanged. No reported GPIO/persistence/
cleanup/watchdog failure. Startup AUTO persistence is acknowledged but not yet
exercised by another boot; edge_no_catchup and logical-OFF startup remain. Physical
Flood polarity confirmation pending. Garden native settings UI unlock not published.
Pin/input/clock resource remapping remains maintenance-only; reassess live-edit
and lights-only OTA policy BEFORE connecting power equipment. Main power is LIVE;
no historical bare/main-OFF isolation applies now.

## Earlier: overhead control confirmed; daily 08:00 ON / 20:00 OFF AUTO enabled

After operator-attended main restoration, Jeremy observed overhead OFF, then
confirmed the single API ON physically turned it ON. He subsequently reported
app control working. Other channels were not live-tested. On explicit schedule
request, eight pure isolated Lua evaluations verified 08:00 ON, 20:00 OFF,
removal of the old 21:00 OFF edge, midday hold, switch ON/OFF, missing-time hold
and midnight no-catchup. These evaluations never changed live inputs/outputs.

Exactly ONE fresh revision/boot-guarded patch changed only Overhead(pin18)'s
existing OFF edge 21:00->20:00 and current AUTO false->true. Existing 08:00 ON
and wall-switch edge logic retained. Seattle/LA clock synchronized/valid with
PST/PDT. Read-back verified rule/current AUTO, other eight/profile/defaults
unchanged, same healthy active GPIO boot/layout and no reported relay/cleanup/
watchdog error. Current overhead logical ON; actual future daily edges unobserved.

**Startup AUTO remains false** with logical-OFF boot default: reboot starts
manual OFF, not scheduled AUTO. The rule is persisted, but current AUTO does not
override the separate boot default. Default-AUTO change alters the armed layout
and needs isolated disarm/reboot/edit/rearm; no live USB/reset/layout mutation
was performed. Manual app commands also disable current AUTO; re-enable it to
resume schedules. Original production snapshot is historical (old 21:00 rule),
NOT something to blindly restore over this newly requested 20:00 schedule.
Private evidence: `overhead-schedule-0800-2000.execution.local.json`.

## Initial migration evidence

- Attached ESP32-S3 / 16 MiB; different chip identity from Sunroom2.
  Secure boot and flash encryption disabled.
- Entire original 16 MiB flash streamed directly over SSH into the encrypted
  shelf vault, without a raw-flash file on Drallion. Independent device full-range
  MD5 matched the read, and shelf SHA256/MD5 matched the transfer proof.
  Backup/digest operation took 460.55 seconds. No original-image restoration tested.
- Read-only offline LittleFS mount recovered 36 files / 263,137 bytes.
  Actual hostname Barn, nine relays, S3 external-antenna N16R8 board configuration
  and private Wi-Fi material confirmed. Definitions/rules/polarity/defaults match
  the earlier API export. Zero logical ON boot defaults, one AUTO boot default;
  this is not contact-safety proof or approval to arm.
- Frozen native app exactly matches the build proven on unarmed Sunroom2:
  `relay-profile1`, 950,736 bytes; file SHA256
  `89efc07c6374c0dae52f65aeb1be1afdd5ea0a066662eb99d2153ac5d74c4500`;
  ELF `65cae0c07d327430d5d32c5b5ca6186c308ffc355b8e20bbc78a05b4c96b1c6b`.
- The one-shot execution acknowledged identity/security/geometry, ERASE, WRITE
  and VERIFY. All FOUR bootloader/partition/OTA-data/application digest checks
  passed. An explicit first reset was issued using the same open serial session.
- No arm command or adapter reopen was issued by the worker.

## Earlier: GPIO ACTIVE under main-OFF isolation; physical light test pending

Jeremy confirmed the requested native-USB unplug/replug with equipment main
power kept OFF. LAN-only checks verified a NEW healthy valid boot versus the
arming boot, exact expected chip/ELF, GPIO active=true, armed=true and simulated=
false. The complete manual test profile is unchanged: all nine current/default
values false and AUTO/defaultAuto false. No per-relay last_error, cleanup failure
or current/previous watchdog timeout. Two subsequent LAN checks retained the
same healthy active boot. LA/network clock synchronized/schedule-valid after
this restart, proving saved clock configuration across reboot. No serial open,
reset command or output-toggle command in these checks.

This is the first controller GPIO activation, NOT proof of physical relay/contact
polarity, safe electrical OFF, wall switches, live loads or sensors. Main power
remains operator-reported OFF; coordinate attended restoration and observe actual
overhead state before an overhead-only API test. Other eight channels stay
manual/logical OFF, not commissioned. Stop/re-isolate on unexpected load behavior.
Don't casually reopen serial or restore production AUTO/defaults. Private evidence:
`gpio-activation-current.local.json`, `gpio-active-stability-check.local.json`.

## Earlier: USB arming saved for manual-OFF test layout; activation pending

On 2026-10-20 Jeremy explicitly reported equipment main power OFF, native USB
connected to Drallion, and requested GPIO enable. Fresh USB identity/image/health/
clock review found all nine current/default values false. Only Overhead(pin18)
had current/default AUTO true. The complete current production profile was
preserved privately; ONE revision/boot-guarded patch disabled only those two
Overhead AUTO fields. All nine are now manual/logical-OFF with manual-OFF boot
defaults; labels/rules/pins/polarity/clock/sensors unchanged. No physical OFF
contact safety is inferred from these logical values.

After fresh chip/ELF/boot/layout/profile/healthy/valid/watchdog and synchronized
clock gates, exactly ONE USB `io_arm` with exact confirmation/identity/layout/
boot was acknowledged. Read-back confirmed the saved layout armed and GPIO
still inactive. No reset command, physical light test, other output command or
main-power restoration. Two later LAN snapshots after closing USB retained
healthy valid expected image, armed=true, **GPIO active=false**, all nine manual
OFF and no cleanup/watchdog fault. All serial sessions closed.

**Next attended step:** normal unplug/replug of the SAME native USB while main
equipment power remains OFF, then LAN-only verification of real active GPIO,
manual-OFF/defaults and faults BEFORE any equipment-power/live-light step. USB
opening may itself restart/activate the saved arm; do not open it casually now.
`remote_controller_arm.py` deliberately does not reboot/retry; six fake tests
cover exact identity/boot/layout command, permission/manual-default gates,
lost ack/reboot without replay. Private original/journals remain intact.

Restoring production `defaultAuto` later changes the armed layout and needs its
own disarm/reboot/edit/rearm plan, NOT a blind full-profile replay. Runtime AUTO
and boot defaults are distinct. No automatic restoration or live-output test
is authorized just by finishing this arming metadata step.

## Earlier: circuit-powered LAN boot + Seattle clock verified — 2026-10-20

Jeremy removed laptop USB, restored equipment main power and reported overhead
lights ON. GET-only checks verified Barn online at its prior address with exact
expected chip/working ELF, healthy valid firmware, Wi-Fi connected and GPIO
**inactive/unarmed**. The unique `Overhead` definition is pin18, AUTO true,
logical value false. Thus physical lights ON is NOT evidence of GPIO control;
logical OFF is not contact feedback and cannot establish load safety.

Jeremy separately approved Seattle time. Exactly ONE fresh boot/revision-guarded
clock-only patch set `America/Los_Angeles` + network source. Read-back verified
unchanged nine definitions/defaults/AUTO and all other fields, same healthy boot,
inactive/unarmed GPIO, synchronized valid schedule clock, local PDT and host UTC
within 15 seconds. `edge_no_catchup` retained. Clock patch not yet reboot-tested.

NO light/output commands or arming were sent: a simulated logical edit would not
switch physical lights. Actual overhead control needs separately reviewed USB
activation/physical commissioning, including all-channel startup effects; don't
silently arm a restored production profile/AUTO on live equipment. Previous
main-OFF USB maintenance approval is no longer applicable; re-isolate equipment
before another serial/activation session. Current wiring/contact behavior is
not commissioned. The clock edit does not authorize output activation.

## Earlier: native USB setup + nine-relay/Wi-Fi restore PASSED — 2026-10-20

Jeremy explicitly approved native USB input support while keeping the same
connection and main-power isolation. The working RX-fixed image, exact hashes,
transport design/tests and remaining gates are in [NATIVE_USB_SETUP.md](NATIVE_USB_SETUP.md).
It preserves UART logging, uses separate bounded source-routed setup streams,
and boots healthy/valid. Its native USB initial-restore journal acknowledges ONE
nine-relay import and ONE private credential provision, both read back. Wi-Fi
connected; independent LAN GETs after USB closed verified the same healthy boot,
exact chip/ELF/profile/layout, inactive/unarmed GPIO and zero watchdog timeout.

A later native USB transport check passed 12 profile GETs, exact 12,288-byte GET,
oversized-frame 400 rejection and subsequent recovery GETs, preserving boot/edit
revision/layout. All readers closed. No GPIO activation, live equipment operation,
controller OTA, Garden publication or source commit/push. Original full backup
and all earlier interrupted/candidate journals remain intact; NEVER replay them.

A later native session was observed on a NEW boot, which remained stable through
transport tests and subsequent LAN checks. It retained all nine definitions and
Wi-Fi, activated hostname `barn`, and reported SDK reset reason ESP_RST_USB (11),
not a task-watchdog timeout. Exact opening/control-line transition was not isolated.
This verifies persistence across an observed USB restart, not untouched cold-power
or brownout behavior. USB opens must still be treated as potential restarts.

**Current remaining gates:** clock still manual/null/unconfirmed, physical relay/
switch/startup and cold-power tests, and Barn OTA unproven. Keep equipment main power OFF and the working native USB
connection until the next expressly coordinated maintenance step.

## Earlier: native USB socket boots correctly — 2026-10-20

Jeremy moved the cable from CH340 USB-TTL to the board's native USB socket.
Drallion enumerated the ESP32-S3 USB JTAG/serial interface as ttyACM0. A bounded
12-second PASSIVE capture (no transmitted commands, explicit reset or flash)
recorded SPI_FAST_FLASH_BOOT, BENCH_PASS, RUNTIME_READY and RUNTIME_STATE,
with no panic/download marker. This establishes normal native startup on that
socket, not a repair or diagnosis of the CH340/RET path.

Startup summary: `relay-profile1`, ONE factory relay, GPIO inactive, simulated
mode, Wi-Fi unprovisioned, manual/unconfirmed clock. The nine-relay profile and
credentials have NOT been restored. No output arm occurred. All readers closed.

Current firmware `serial_task()` explicitly reads `uart_read_bytes(UART_NUM_0)`;
native USB is a secondary OUTPUT console only. Source review confirms it cannot
receive setup RPC on ttyACM0. Keep this working USB/power arrangement and main
equipment power OFF. Next needs reviewed UART0 access or a separately reviewed
native USB input enhancement; do not repeatedly switch/reset/reflash or claim
Wi-Fi/restore completion. The original verified backup remains intact.

## Earlier startup check — after operator cold USB replug, 2026-10-20

After Jeremy replugged USB with all serial sessions closed, another bounded
GET-only inspection captured ROM download mode and no native RPC response.
A normal serial-open reset remains a possible contributor; this does not prove
what an untouched cold boot did before inspection. Configured Barn relay/input
pins do not include GPIO0; actual physical wiring/button state is unverified.

A single supported esptool S3 **watchdog reset** was subsequently issued while
holding the same USB session. Bounded startup capture again showed ROM download,
not RUNTIME_READY. No further reset retries, flash writes, profile import,
credential provision or GPIO arming were issued. All sessions are closed and the
TTY has no remaining owner. Stop repeated reset/flash attempts; coordinate a
board/USB/BOOT/GPIO0 wiring photo/visual check and, if appropriate, a separately
agreed power-only bare-board check with equipment main power OFF. Do not resume
Sunroom2 RET-button diagnosis or infer a shared physical cause.

Before that one watchdog reset, a no-reset ROM connection failed to synchronize,
then a standard connection stopped at an overly strict bootstrap-data comparison;
neither attempt reached watchdog reset/setup. A targeted READ-only digest audit
confirmed the bootloader, partition table and application still match EXACTLY.
Only OTA-selection data differs from the erased bootstrap template, which is
expected mutable boot/health state, NOT evidence of corrupt firmware. The resume
worker now compares immutable images and requires coherent valid ota_0 boot
selection through native API before any restore. No automatic reflash was used.

`remote_controller_resume.py` and nine fake tests cover fresh factory vs exact
already-restored profile, unexpected state refusal, lost replies without replay,
identity gates, immutable-digest reset gate and mutable OTA metadata. Private
credential transfer remains SSH stdin/process memory only. Its restore path was
NOT reached on real hardware. It must NOT be blindly rerun from this checkpoint.

## Earlier resume inspection — 2026-10-20

Drallion returned after Jeremy woke it. The original root Python worker still
owned ttyUSB0; its exact executable/argv, parent and descriptor were verified,
then SIGINT terminated that owned worker. Exit and serial release were confirmed.
No second writer was opened while it remained active.

A subsequent bounded GET-only inspector captured **ROM `waiting for download`**
and received no native RPC response. This confirms download mode at that point,
not bad flash, not when the mode was entered, and not a specific strap/reset cause.
No flash/config/credential/arm/reset command was issued on resume. The inspector
closed and the TTY has no remaining owner. An initial inline inspector had a
syntax error before execution/TTY opening; its corrected file was compiled
before execution. Raw logs stay private.

**Next step at that checkpoint (now completed/superseded above):** operator normal USB unplug/replug with serial tools closed,
equipment main power still OFF. Then inspect native identity/health/profile/Wi-Fi
before any setup. Do not reflash or blindly replay setup. The old worker can no
longer continue, but actual persisted profile/credentials still need read-back.
This startup observation is analogous operationally to Sunroom2 HW-001, not proof
of the same cause and not renewed RET-button diagnosis.

## Earlier stop / uncertainty boundary

SSH to Drallion was lost after the `first_reset_issued` event. A follow-up SSH
attempt timed out too. No native-ready/healthy/profile-import/private-credential
acknowledgements were received. A GET-only check at Barn's earlier address did
not confirm the native controller. Do NOT equate this with bad flash: all four
image verifications already passed. Do NOT reflash or replay provisioning.

The remote Python worker may still own the TTY or continue after connectivity
returns. The caller journal and streamed stage events are authoritative evidence
of acknowledgements, not a guarantee that unacknowledged work never happened.
First restore Drallion reachability, inspect the actual process/TTY owner and
board state, and coordinate/release that worker before opening another session.
Do not run a second writer. Keep equipment main power OFF, USB attached and
preserve the original journal/recovery material.

Intended profile retains the nine reviewed translated rules/pins/defaults,
**GPIO unarmed, sensor acquisition disabled, timezone null/manual/unconfirmed**.
These settings were prepared privately, but their import is NOT yet confirmed.
Likewise Wi-Fi restoration and hostname activation are NOT yet confirmed.
Do not assume the board can already join Wi-Fi: the original NVS was erased.
Barn's historical clock discrepancy remains unresolved; do not silently import
it or infer confirmation from Sunroom2's separately approved LA clock.

## Tooling / follow-up

- `remote_flash_backup.py`: identify/read-only RAM-stub worker; all raw flash
  transported directly to the mounted private vault. No flash writes/reset-to-app.
- `extract_legacy_flash.py --expected-hostname barn`: expected hostname/count
  gates, explicit read-only LittleFS mount with no auto-format, reviewed AST Lua
  translation; default remains Sunroom2 for backward compatibility.
- `remote_controller_bootstrap.py`: one-shot isolated Barn bootstrap and intended
  same-session restore, with exact chip/security/artifact gates, no retry,
  no arm/reopen, private credentials only in SSH stdin/process memory. Only
  generic public binaries/tools were staged in a temporary Drallion directory.
- Eleven fake worker tests plus 24 existing uploader/release tests pass offline.
- After the disconnect, the worker source was hardened to set a finite serial
  read timeout explicitly and check the deadline immediately after a read.
  esptool can leave blocking serial settings, making a loop deadline insufficient.
  This local change does NOT affect an existing remote process, is not a proven
  explanation for Drallion's loss of connectivity, and is NOT a reason to rerun
  its flash path. A recovery session must start with actual-state inspection.

All raw logs, identities, Wi-Fi/config, original full flash and exclusive private
execution journals remain under the manually unlocked encrypted vault, reachable
through `garden-device-backups/current-barn-usb`. No commit/push/publication,
router/service change, GPIO arm, live equipment test or Sunroom2 operation was
performed in this Barn task. See [COMMISSIONING.md](COMMISSIONING.md).
