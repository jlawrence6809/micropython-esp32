# Known issues and accepted deferrals

## NET-001 — Sunroom2 intermittent Wi-Fi association, observed 2026-10-27

Jeremy reported AC power OFF and Sunroom ESP32 connected to Drallion native USB
for diagnosis. Initially its old IP/mDNS did not respond. No reset/config/flash/
arm command was sent. Passive native capture (18 s, no TX) contained only a fixed
bootloader application-loaded message, not enough to determine runtime health.
SSH exit timed out, but remote lifecycle reported finished and independent PID/
TTY-owner inspection confirmed it exited/released the port; no reader remains.

Read-only OpenWrt records confirmed exact expected MAC retained its old DHCP IP
and completed DHCP exchanges. AP logs included successful association/key handshake
and later inactivity removal/missed authentication-response ACKs. Subsequently
router, Drallion AND shelf API requests all succeeded without a settings change.
Exact Sunroom chip/previous logging-only ELF verified, healthy/valid ota_1, eight
persisted definitions, GPIO inactive/unarmed, saved Seattle/network clock. Runtime
status reported POWERON reason1, uptime >15 min, no current/previous watchdog mask.

Wi-Fi reported eight disconnects in that boot, latest reason7 (SDK
CLASS3_FRAME_FROM_NONASSOC_STA: association-state error, NOT proof of wrong password
or a specific hardware fault). Signal then ~-61 dBm. Seven 10-second-spaced LAN
samples all succeeded in the SAME healthy boot, disconnect count stayed eight,
signal -62 to -55 dBm. Short-term recovery is observed, NOT a fix or long-term
reliability proof. No sufficient evidence to blame antenna, AP roaming, firmware,
normal AC supply or a particular USB transition; original circuit-powered failure
remains unproven. Successful USB boot does not establish normal-supply reliability.

Private evidence in Sunroom vault: `returned-path-comparison-current.local.json`,
`returned-full-lan-snapshot.local.json`, `returned-usb-wifi-stability.local.json`,
router/lease captures and passive capture lifecycle. Credentials/flash unchanged;
no reason to replay provisioning or reflash. Further useful work is correlated
AP/client association diagnostics, and only separately coordinated normal-supply/
UART observations if needed. AC remains operator-reported OFF. Old image's native
USB is logs-only, not a setup-command transport. Barn policy/arming approval does
NOT apply to Sunroom. HW-001 button/strap experiments remain deferred; this LAN
inspection did not resolve or resume them.

### Follow-up AP correlation, 2026-10-27 (read-only)

Checked ALL wireless interfaces/station tables on all five pinned OpenWrt nodes;
none held an active Sunroom station at capture. Deco's live default AND per-node
client query positively identified exact Sunroom MAC as online/wireless/main
2.4 GHz on X20-Outdoor. This is stronger evidence than an old DHCP lease or the
absence of a Deco client while it was associated elsewhere. Credentials were
consumed in memory through the existing SDK loader; no credential print/copy or
router configuration changes.

Earlier OpenWrt logs contain attempts across nodes and completed key handshake
on a tenant AP followed shortly by disconnect. Captured buffers showed no AP
restart markers and no other-client disconnects around that event. No nondefault
11r/PMF setting was established by the selected non-secret UCI queries; omitted
options do NOT prove effective runtime defaults. Client/AP compatibility,
selection/roaming, radio/power causes remain hypotheses, not a proven diagnosis.

Final API snapshot: SAME healthy POWERON boot at 2,004 s uptime, disconnect count
still eight versus 935 s initial snapshot (no new reported disconnect events over
17+ min), RSSI -61 dBm, GPIO inactive/unarmed. This does not prove continuous
packet availability or normal circuit-supply reliability. No firmware, credential,
Wi-Fi preference, power-save, reset or GPIO mutation performed. Current firmware
lacks BSSID/channel and per-event reconnect history; a separately approved
instrumentation update would allow a controlled per-device AP-selection or
power-save experiment without blind router changes. Do not infer Sunroom OTA
permission from Barn's separate lights-only maintenance approval.

Private evidence: `sunroom-ap-association-current.local.json`,
`sunroom-deco-confirm-current.local.json`,
`sunroom-wifi-investigation-checkpoint.local.json`. sysfs forwarding-table reads
were inconclusive; missing `bridge` utility was NOT installed or worked around
with host/service changes. No serial reader left running.

### Diagnostic OTA and reproduced symptom, 2026-10-27

With explicit user approval, one guarded AC-OFF/USB-powered UNARMED OTA installed
read-only BSSID/channel/PS/history diagnostics on the current tested native base.
Expected new healthy/valid ota_0, eight definitions/layout/Seattle clock retained,
GPIO inactive/unarmed. No network/credential/profile/PS/AP change or USB/reset
intervention. Native USB setup is now supported by that cumulative base; older
'logs-only' and 'missing BSSID/history' notes above describe the BEFORE state.

First trace captured successful OpenWrt tenant-b association/DHCP at -52 dBm,
then reason34 MISSING_ACKS at -51 dBm only a few seconds later. Other attempts
failed with association reasons7/4; channel3 association succeeded at ~71s.
Fresh Deco live-client query confirmed Sunroom on X20-Outdoor wireless2.4GHz;
SDK-advertised BSSID is not directly interchangeable with its live ESP BSSID.
Seven disconnects/all20 events retained, no truncation; follow-up reads stable.
Current PS=MIN_MODEM(1). Power-save interoperability is a candidate for separately
approved testing, NOT a proven cause or a change already made. Current normal-AC
supply reliability remains unknown; no HW-001 button investigation resumed.

See [WIFI_DIAGNOSTICS.md](WIFI_DIAGNOSTICS.md) for image hashes, privacy/concurrency
and policy/testing details; private raw history/journal remains in Sunroom vault.

### Subsequently approved Sunroom PS-OFF trial, 2026-10-27

One separate guarded OTA installed a build-local default-OFF modem-sleep override,
enabled ONLY for this Sunroom trial. Expected healthy/valid ota_1, GPIO still
inactive/unarmed, eight definitions/layout/Seattle clock preserved. Reported PS=0
(NONE), not just an assumed setting. Barn/APs/shared defaults unchanged.

Five initial OpenWrt failures (four reason7 and one reason2 at very weak signal),
then same Deco BSSID/channel3 at ~35s; stable14 events/five disconnects through
300s uptime. This did NOT fix startup OpenWrt association. No successful OpenWrt
association this boot, so effect on prior post-DHCP reason34 remains untested.
Four reachable OpenWrt radios all reported channel1; tenant-a SSH unavailable on
this pass. Vendor/channel confounded. A Barn AP residual Sunroom station was
explicitly unauthenticated/unassociated, not a second successful connection.

PS_OFF test firmware remains installed (higher consumption), no automatic revert,
forced reconnect or additional reboot. AC OFF/USB isolation continues. See
WIFI_DIAGNOSTICS.md for current image hashes/tests/private provenance. Root cause
and normal-supply/HW-001 reliability remain unresolved.

### Read-only ACK/authentication correlation, 2026-10-27

AP logs now independently confirm the exact reason34 sequence: tenant-b completes
association/WPA key exchange, primary DHCP ACK same second, then tenant-b explicitly
evicts for excessive missing ACKs ~4s later. So this was not a bad-password/DHCP
failure. An auth-response-not-ACKed warning preceded successful association; don't
classify every such warning as proof the whole join failed.

PS_OFF boot failures correlate with auth-response-not-ACKed warnings at ALL five
APs; later bounded reads filled earlier transient SSH gaps. 62 enabled Wi-Fi/PHY/
coexistence SDK settings match frozen Barn/Sunroom; live SSIDs match. WPA2-PSK,
standard basic rates/WMM and low-ACK policy observed; no obvious security mismatch.
Exact stored station parameters aren't all API-exposed; not proven byte-identical.

Evidence points to unreliable low-level exchanges or AP/driver reporting, but
without independent over-air capture cannot distinguish them. Further single-AP
bounded/recovery-safe test or radio capture needs separate approval; none performed.
Same healthy valid PS_OFF boot, inactive/unarmed GPIO, definitions/clock preserved;
Barn remains zero-disconnect. Private `wifi-auth-analysis-current.local.json` and
WIFI_DIAGNOSTICS.md preserve details. No router/firmware/host change in this phase.

### External-circuit isolation result, 2026-10-27

Operator disconnected external circuit/power-cycled USB to test excess loading.
New healthy valid POWERON boot with actual PS_NONE0, GPIO inactive/unarmed:
tenant-a association/IP succeeded, then reason34 at63.133s / ~-40dBm. Other AP
failures then Deco at~138s. Same boot/counts through249s; no reboot during failures.
Thus external circuit and modem sleep aren't necessary for this failure. Does NOT
exclude USB cable/source/onboard-regulator sag without reset, RF/interference or
software/driver issues. No electrical measurement or serial/capture intervention.

Circuit currently DISCONNECTED per operator; keep antenna/USB and unarmed state,
no automatic reconnect/restore. Further one-variable power/cable or bounded AP
trial requires coordinated action. Evidence: WIFI_DIAGNOSTICS.md and private
wifi-bare-board-current pointer. Deferred RET/normal-supply issue not reopened.

### Controlled single-AP / independent monitor result, 2026-10-27

Approved 20s fixed-primary AP trial restored original auto selection, then known
PS_OFF baseline firmware was deliberately restored. Each OTA exactly one fenced
POST; expected healthy valid slots/profile/clock retained, GPIO inactive/unarmed.
No temporary trial firmware left deployed. Living-room independent monitor/tools
removed, all owned PIDs gone, AP enabled, network/wireless hashes unchanged.

Observer saw Sunroom auth requests, primary success replies at6Mbps with three
retries each, no corresponding ACK/association request in two exchanges. This
supports real low-level exchange trouble, not a password/DHCP problem, but does
not prove a faulty board: independent reception isn't Sunroom reception, missing
capture isn't RF absence, FCS not included. Local RF/board/interoperability remain.

Initial observer setup failed on ip-tiny alias syntax BEFORE any upload and was
retired with zero firmware uploads and complete cleanup; distinct attempt succeeded.
Capture stdin filter wasn't applied by this tcpdump reader; unrelated frames were
removed within vault, only targeted packet evidence retained. See SINGLE_AP_TRIAL.md
for exact limits/tests/hashes/provenance and a matched-spare/proximity next option.
No further physical/network test, GPIO or RET investigation implicitly authorized.

## HW-001 — Sunroom2 RET/reset can select ROM download mode

**Status: deferred at Jeremy's request, 2026-10-16.** Stop the hardware investigation
for now; no further button, meter, port or firmware experiments are requested.
This accepts a known bring-up limitation, not live-output commissioning or a
claim that standalone startup/recovery is fully reliable.

### Verified observations

- The physically isolated Sunroom2 ESP32-S3-N16R8 board has two USB-C sockets,
  an external antenna, and adjacent buttons printed RET and BOOT.
- Successful boots ran the expected diagnostic-free `relay-profile1` image,
  passed startup/health checks, restored Wi-Fi, activated the `sunroom2`
  hostname, and retained all eight reviewed relay definitions, translated Lua
  rules, defaults and layout. GPIO was inactive and unarmed.
- A successful no-serial-open cold boot was verified over the network on
  Drallion USB. A successful cold baseline was also verified after switching
  the single cable from the CH340/UART socket to the native Espressif USB socket.
- UART captured a working `SPI_FAST_FLASH_BOOT`, followed by a physical RET/EN
  reset selecting `DOWNLOAD(USB/UART0)` and `waiting for download`, with no
  subsequent native application startup. This failure is before Lua/Wi-Fi code.
- In an active, timestamped capture, printed BOOT alone produced no reset;
  printed RET alone with a nonmetallic probe produced another ROM download
  reset. These results fit the printed roles; reversed labels and accidental
  simultaneous button presses are not established explanations.
- A native-USB RET reset also failed to regain the network during a bounded
  35-second window, but its boot mode was not captured. Do not infer its exact
  failure mode from network unreachability alone.
- Some shelf/charger startup checks failed. Conversely, a controlled UART-reader
  close retained the SAME healthy network boot at 2 and 12 seconds. Neither
  USB close, ModemManager, a particular host nor one socket is a proven sole cause.

**Unknown:** precise GPIO0/strap, reset circuit, USB modem-line, board/power or
other cause. No electrical measurements or board modifications were performed.
No firmware fix has been applied. See [COMMISSIONING.md](COMMISSIONING.md) for
chronological evidence and diagnostic boundaries.

### Operational consequences and boundaries

- A ROM-download boot has no automation, Wi-Fi API or native OTA service.
  Physical recovery access may be necessary; do not rely on networking to recover
  a device that never reached the application.
- Physical RET, software restart, OTA restart, watchdog restart and power-on are
  distinct paths. Success/failure of one does not prove the others. One subsequent
  attended UNARMED controller OTA/software reboot PASSED without any USB open or
  RET press; profile/clock/network and healthy new boot were verified, with three
  later stable checks. See [CONTROLLER_OTA.md](CONTROLLER_OTA.md). That does not
  resolve HW-001 or establish active-output/unattended/power-loss recovery.
- Do not repeat profile import, Wi-Fi provisioning, erase or flash operations as
  a response to lost reachability. Those settings were acknowledged and their
  persistence was subsequently verified. Inspect actual state before any write.
- A complete power cycle has yielded successful boots, but is NOT documented as
  a guaranteed recovery on every tested supply/port. Avoid promising a universal
  workaround or leaving a bootloader-entry command as a normal startup step.
- Serial adapter opening/closing and modem-line changes can reset hardware.
  Maintenance isolation/operator approval is still required, including for
  apparently passive logging. Do not connect both board USB sockets at once.
- Original full 16 MiB flash was backed up and independently verified. Original
  image, private configuration, photographs, journals and raw captures remain
  in the encrypted private-services vault, not Git. Logs may contain SSIDs and
  private identifiers; sanitize reports. No restore was executed.

### Current bring-up state at deferral

- Native firmware installed and verified; eight-relay profile and Wi-Fi restored.
- Physical GPIO **never armed**; no relay/contact, wall-switch, polarity,
  brownout or live-equipment commissioning performed. Barn unchanged.
- Jeremy confirmed Seattle / `America/Los_Angeles` with automatic PST/PDT.
  After an operator replug on Drallion's USB-TTL socket, one fresh boot/revision-
  guarded atomic patch applied that zone and the network rule clock. Read-back
  verified SNTP synchronization, a valid schedule clock and retained
  `edge_no_catchup`, all eight relay definitions/defaults/AUTO and the same
  healthy boot. GPIO remained inactive/unarmed. No reset or serial session was
  used; persistence of this latest clock change was not separately reboot-tested.
- Garden native adapter/lab tests exist, but production publication/actual-phone
  checks remain separate work. No application publication is implied here.
- All UART captures are stopped; no further RET hardware investigation is running.
- A separately approved logging-only firmware update was uploaded ONCE over
  guarded Wi-Fi OTA, switched to the other slot, and reached the expected healthy
  valid image with inactive/unarmed GPIO. The new startup summary logs contract,
  relay count, active-GPIO flag, clock source and timezone-confirmed flag, not
  credentials or identity/fence tokens. The executor intentionally refuses armed
  controllers pending physical/reboot/maintenance-policy review.

Reopen this issue only with explicit scope. Deferring it does not authorize GPIO
arming, reconnecting loads, controller OTA execution or unrelated host changes.
