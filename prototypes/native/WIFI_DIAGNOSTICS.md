# Read-only Wi-Fi diagnostics — Sunroom2, 2026-10-27

**Latest state:** A separately approved Sunroom-only PS-OFF trial below is now
installed (mode0), healthy and unarmed. It did NOT fix initial OpenWrt association.
A subsequent operator-reported bare-board isolation also reproduced reason34 at
strong signal with PS_OFF, within one POWERON boot; external circuitry remains
disconnected and GPIO unarmed. No automatic reconnection/reboot/revert performed.
The first diagnostic-release sections describe the earlier read-only/mode1 phase.

## Scope and API

Jeremy approved a diagnostic firmware OTA with Sunroom AC OFF and the ESP32
USB-powered by Drallion. No Wi-Fi preference, power-saving, credential, relay
profile, GPIO arming or router setting changes were authorized/performed.

The current tested native base is cumulative: it also includes Barn's native-USB
setup transport and live-relay-setting capability. This does NOT arm Sunroom or
use those mutation paths. Initial physical activation remains a separate USB
operation with exact review; Sunroom remains inactive/unarmed.

`GET /api/config` advertises `wifi_diagnostics:true`.
`GET /api/wifi/status` additionally reports, when available:

- `sta_bssid`, `sta_channel`, numeric IDF `sta_authmode` from current AP info;
- numeric `power_save_mode` from the SDK getter: NONE=0, MIN_MODEM=1, MAX_MODEM=2.

`GET /api/wifi/diagnostics` reports format_version1, boot_id, current uptime_ms,
capacity32, total/overwritten counts and the retained events in append order:

- station_start, connect_attempt, associated, got_ip, disconnected,
  connect_call_error;
- sequence, monotonic uptime_ms, BSSID (null if unknown), channel/RSSI/authmode
  (null if unavailable), numeric disconnect reason and SDK connect-call error.

SSID/password/IP payloads are NOT copied into history. AP identifiers and raw
responses still belong in private captures, not public logs. No history-clear,
reconnect, preferred-AP or power-save mutation endpoint is added. A reason code
is a reported symptom, not proof of which driver/radio/power component caused it.

## Resource and concurrency behavior

History is a fixed 32-entry volatile RAM ring; no allocation, flash, logs, SDK or
network calls in its pure module. Callback/network task append and HTTP snapshot
copy use a dedicated short critical section. JSON/SDK queries run outside it;
no runtime/NVS mutex is acquired by the new event recorder. Existing association/
DHCP/retry/backoff and clock handling are retained. Timestamp is captured on entry;
concurrent append sequence is recording order, not a guarantee of causal ordering
for events on different tasks. Counts/history reset on reboot, overwritten_events
makes truncation explicit. Retrieve history before a reset when possible.

## Host/build verification

- Actual C ring tested: empty/bound/overwrite/order, value copying, independent
  snapshots, beyond-32-bit timestamps/sequences, event names/unknown BSSID.
- Actual runtime JSON serializer tested with fake timer/critical section: complete
  bounded output, nulls/fields, no SSID/password, no allocation or SDK stub call
  while holding the history lock.
- Actual backend/profile/commit host fault tests, 25 offline OTA tests and eight
  release regressions pass. Dedicated controller build seeded from Sunroom's
  frozen SDK config passed; physical selftest/stall/rollback-injection flags OFF.

## Unarmed equipment-power-OFF OTA policy

The uploader adds a truthful alternative to literal bare-board approval:
`--apply --maintenance-confirmed --equipment-power-off-confirmed
--remote-reboot-confirmed` requires an UNARMED coherent controller; attached wiring
is not falsely declared absent. This mode is mutually exclusive with lights-only
armed maintenance. Original default bare/unarmed policy remains.

All identity/image/fence/double-snapshot/health/Wi-Fi/config/slot/clock checks,
exclusive private journal, one POST/no replay and no implicit arm/restore remain.
`--verification-timeout` optionally allows 15..600 seconds of GET-only recovery
polling (default120), useful for observed slow Sunroom association; it never causes
another upload. A failed image/connection can still need physical recovery.

## Verified execution / first new evidence

Frozen ESP32-S3 `relay-profile1`, 955,104 bytes.
Image SHA256 `4b8a0ff54ad2575879d695dcee41fda209965fec628d660bf4a31c2c3640103a`.
ELF SHA256 `2462b5a3ac9d279888d902f78ab5399e3fa363b4a8864f427b25dcd76c659d23`.

Original recovery backup rehashed; frozen source hashes checked. Exactly ONE
fenced OTA POST acknowledged, ota_1 -> ota_0, expected healthy/valid new image,
GPIO inactive/unarmed, eight-relay profile/layout and Seattle clock retained,
network reconnected. No USB open/reset intervention/settings restore/arming.
Three subsequent checks retained the same healthy boot and coherent diagnostics.

History immediately reproduced the association problem:

- ~2.55s: associated to OpenWrt tenant-b on channel1;
- ~3.74s: DHCP/IP obtained, RSSI about -52 dBm;
- ~6.35s: disconnected, reason34 MISSING_ACKS, RSSI about -51 dBm;
- other retries: reason7 CLASS3_FRAME_FROM_NONASSOC_STA at several OpenWrt APs,
  one reason4 ASSOC_EXPIRE, signals ranging from strong to weak depending on AP;
- ~70.79s associated / ~71.83s got IP on channel3, then stable.

Fresh Deco per-node client query independently confirmed Sunroom online/wireless
2.4GHz on X20-Outdoor. Its SDK-advertised BSSID did not directly match the live
ESP BSSID, so do not silently equate those identifier fields. Current power-save
mode1 (MIN_MODEM); first capture retained all20 events, seven disconnects, no
truncation. Follow-up reads held event/disconnect counts steady.

This narrows the symptom to missing acknowledgments/association handling even at
strong signal. Power-save/AP interoperability is a candidate for a separately
approved single-device test, NOT established as the cause. No such test was
performed in this update. No normal-AC-supply, physical GPIO/contact, long outage
or power-cut/rollback proof follows from this diagnostic success.

## Separately approved PS-OFF trial — 2026-10-27

Jeremy explicitly requested the Sunroom-only power-save-off test, continuing
AC-OFF/USB-powered/unarmed maintenance. Added build-local default-OFF
`CONFIG_GARDEN_WIFI_DISABLE_MODEM_SLEEP`; only dedicated test SDK config enables
it. Actual helper calls `esp_wifi_set_ps(WIFI_PS_NONE)` after init/STA mode and
before tasks/association; ESP_ERROR_CHECK propagates failure rather than validating
an unconfigured candidate. No NVS/profile/credentials/AP/BSSID preference edits.
No router/Barn/shared-default/partition/schema changes. Radio consumption rises;
USB success does not establish normal-supply reliability.

Host test compiles actual helper with option OFF/ON, verifies no call when OFF,
NONE/error propagation when ON, init/task order and no enabled shared defaults.
Ring/JSON, actual profile/backend/commit, 25 uploader and eight release tests pass;
dedicated controller build succeeds. Frozen SDK effective setting delta from the
first diagnostic release is ONLY this new flag. Recovery backup rehashed.

Image955,520 bytes; image SHA256
`4f89f710e767da1081bab11cb36a7e44a2e39373786a22d164211176a679d9ac`;
ELF SHA256 `d954bd43e51fd0943d18b8e6dff2ca3ee3f02d8689bac3a340f7142293e7202b`.
Exactly ONE fenced OTA POST, ota_0 -> ota_1, expected healthy/valid new image;
eight definitions/layout/Seattle clock retained; inactive/unarmed GPIO; actual
status PS_NONE0 verified. No USB open/reset/restore/arming intervention.

New trace: first Barn AP attempt failed at weak -87dBm/reason2, then four other
OpenWrt APs failed reason7, including strong -42/-51dBm observations. No OpenWrt
association/IP event this boot. Same prior-confirmed Deco BSSID/channel3 associated
~33.76s / got IP ~34.80s. All14 events retained, five initial disconnects, counts
unchanged at 279/290/300s uptime, actual mode0 throughout, same healthy boot.

**Limited negative result:** disabling modem sleep did not fix startup OpenWrt
connectivity in this trial. It does NOT settle whether PS contributed to the
previous reason34 after a successful OpenWrt association; that phase wasn't
reached. Different AP attempt order means 35s versus 72s is not proof of improved
reliability. No extra forced reconnect/reboot/scan or automatic rollback performed.
Test image remains installed / PS_OFF; further rollback or AP changes are a
separate coordinated operation, not an automatic replay of an old journal.

Read-only AP checks: four reachable OpenWrt 2.4GHz radios all reported channel1;
tenant-a SSH unavailable on that pass. Working Deco uses channel3, so vendor and
channel are confounded, not a proven OpenWrt-specific defect. AP log buffers contain
older entries; missing-ACK counters there are not automatically post-test events.
A residual Sunroom entry on Barn AP was explicitly unauthorized/unauthenticated/
unassociated (signal0); mere station-table presence does NOT establish connection.

Private `wifi-ps-off-release/`, `wifi-ps-off-ota.execution.local.json`, baseline,
first capture, postcheck and AP-correlation records preserve provenance. Keep AC
OFF/USB as-is. No physical GPIO, RET, normal-supply or broader power tests implied.

## Subsequent read-only authentication/ACK correlation — 2026-10-27

Jeremy approved existing-evidence analysis and nonsecret settings inspection only.
No upload/reconnect/reboot/pin/capture-interface/router/credential/arming operation
performed. Fresh GET retained the same healthy valid PS_OFF/unarmed boot, five
disconnects, eight definitions and valid Seattle clock. Barn still reports zero.

Derived approximate boot UTC from host capture time minus ESP history uptime;
router current UTC checks agree within ~1s integer timestamp/SSH precision. This
supports ~1–2s correlation, not millisecond-precise historical clock proof.

**First diagnostic/default-PS boot:** tenant-b at19:10:35 logs an unacknowledged
authentication-response warning, THEN association/AP-STA-CONNECTED, pairwise WPA
key handshake and EAPOL four-way completion. Primary DHCP ACK is at the same
second. At19:10:39 the tenant AP explicitly logs excessive-missing-ACK eviction /
AP-STA-DISCONNECTED, matching ESP reason34 at ~boot+6.35s. Hence the AP really
reported low-ACK eviction; not an inference solely from ESP's reason code. That
attempt used working credentials/security and exchanged traffic bidirectionally.
An individual auth-ACK warning is not by itself proof the entire join failed.

**PS_OFF boot:** precise target-filtered AP logs align unacknowledged auth-response
warnings on all five APs with ESP failure attempts: Barn19:39:57, living19:39:59,
tenant-a19:40:01, primary19:40:05, tenant-b19:40:13 UTC. The tenant-a gap from the
initial SSH-timeout capture was filled with a later bounded read; tenant-b also
answered a later bounded query. No OpenWrt association/IP event in this boot.
Thus disabling modem sleep did not remove these early-join ACK failures.

**Comparison:** 62 enabled ESP_WIFI/ESP_PHY/ESP_COEX-family SDK settings compare
identical between frozen Barn and Sunroom builds. Separate build-local PS-off
flag is the intentional Sunroom override. Live SSIDs match (not printed).
Main BSS settings observed: WPA2-PSK, 6/12/24Mbps basic rates, WMM/UAPSD advertised,
low-ACK eviction enabled; tenant configs explicitly CCMP. Barn live client is
associated/authorized, HT/WMM, not MFP. No obvious security mismatch found.
Omitted generated fields are not universal proof of runtime defaults. API does
NOT expose every saved station scan/PMF/threshold parameter; common zeroed-config
+ PMF-capable provisioning code isn't a direct readback of those stored bytes.

**Limits / proposed next test:** AP logs report its TX/ACK result, not proof from
an independent over-the-air observer. Cannot distinguish real RF/ACK losses from
a driver/TX-status accounting/interoperability fault here. Single-AP bounded trial
with guaranteed return to auto/Deco, ideally paired with management/ACK capture,
is more useful than another guessed global setting. Permanent BSSID pin risks
losing recovery connectivity. Capture-interface setup affects radio/resources and
requires separate approval, especially given MX's custom-driver memory history.
A physical known-good-AP proximity comparison is an alternative only with operator
coordination. Neither test has been run or implicitly authorized by this review.

Private analysis: `wifi-auth-analysis-current.local.json`, timestamped nonsecret
policy/client inspections and tenant follow-up under Sunroom recovery directory.
No new host/network durable configuration or home-network repository edit.

## External-circuit-disconnected / brownout hypothesis trial — 2026-10-27

Jeremy proposed excess attached-circuit current and reported completion of the
power-down/disconnect/USB-power procedure. Physical isolation is operator-reported,
not electrically measured. No firmware/PS/credential/router/arming/serial changes
issued. First LAN read timed out; bounded GET polling recovered diagnostics.

New healthy/valid POWERON(reason1) boot, same PS_OFF image/mode0, GPIO inactive/
unarmed. Trace association to tenant-a at1.583s, got IP6.116s, disconnected reason34
at63.133s with RSSI~-40dBm. Further reasons7/204 during other AP attempts; channel3
Deco associated136.778s/gotIP137.816s. All18 events retained, six disconnects,
no truncation. Same healthy boot/counts in follow-ups at239/249s uptime.

**Negative isolation result:** the missing-ACK failure occurs without the external
circuit attached and without modem sleep. It did not reboot during these recorded
failures; POWERON is expected after the operator USB power cycle, not evidence
of a brownout. Supply disturbances without CPU reset (USB cable/source/onboard
regulator) remain possible, as do RF/interference/driver causes. No electrical
voltage/current measurements or independent ACK capture, so don't claim a board
fault or exclusion of every power issue. Different AP/order/timing means the
~minute association duration isn't evidence of a reliable improvement.

Current physical setup: external circuit DISCONNECTED per operator, USB power,
antenna to remain attached, GPIO still unarmed. Don't silently reconnect wiring
or activate outputs. A coordinated one-variable USB cable/source comparison is
possible next; bounded single-AP/capture remains separately gated. HW-001 RET and
normal-supply reliability are still unresolved, not restarted/fixed by this test.
Private `wifi-bare-board-current.local.json` points to timestamped snapshot,
full history and follow-ups; prior brownout-hypothesis GET saved old boot evidence.

### Subsequent USB cable/port observations

Operator reported proposed cable swap complete. Bounded shelf/Drallion LAN checks
failed; expected native USB by-id was absent on Drallion. No serial opened and
no reset issued; absence did not prove no power, ROM download or a bad cable.
Operator then reported a recurring board USB problem and switching to the other
port (exact host/board socket not assumed). LAN recovered on a new healthy valid
POWERON boot, actual PS_NONE0, GPIO inactive/unarmed. Five OpenWrt failures all
reason7, then same Deco/channel3 at~33.84s;14 events untruncated at113s uptime.
No reboot during recorded attempts. External circuit last reported disconnected.

Port/cable sequence did not resolve the OpenWrt symptom. Cable-only phase lacked
boot diagnostics; don't claim cable versus port effects were cleanly isolated or
a specific supply/strap defect proven. No automatic further power cycle, serial,
firmware/AP/arming change. Private `wifi-usb-cable-current.local.json` and
`wifi-usb-port-switch-current.local.json` point to separate phases.

## Controlled single-AP / independent observer completed

Subsequent separately approved fixed-primary trial and living-room same-channel
monitor capture completed; see [SINGLE_AP_TRIAL.md](SINGLE_AP_TRIAL.md). On-air
successful open-auth replies/retransmissions were observed, without corresponding
ACK/association requests in two failed exchanges. Missing capture isn't proof of
RF absence; hardware/local interference/interoperability still unresolved.

Exactly one trial OTA plus one deliberate baseline-restoration OTA confirmed.
Current deployment is the original PS_OFF baseline (not repeating trial firmware),
healthy valid/GPIO inactive-unarmed, eight definitions/Seattle clock preserved.
All temporary monitor/tools/timer/capture processes removed, observer AP enabled
and config hashes unchanged. Capture stdin-file filter limitation was found;
unrelated frames removed inside vault, only targeted23KiB pcap retained. Future
regular-RAM-file filter fix requires router validation, not another unapproved run.

## Research and Barn control comparison — 2026-10-27

Both controllers use ESP32-S3 / ESP-IDF5.5.1. Fresh GET-only Barn status reported
zero disconnects/last-reason0 over 17+ hours since OTA boot. A fresh station-table
query confirmed authorized/authenticated/associated on the Barn OpenWrt AP,
~17+ hours connected, signal ~-36 dBm, one reported TX retry and zero TX failures.
Sunroom's failing association was a different OpenWrt AP at ~-51 dBm; board,
antenna/location/AP and link conditions are not controlled. Thus no evidence of
this symptom on Barn, and no basis for claiming a universal ESP32/OpenWrt failure.
Barn's older API does not expose actual power-save mode; common source leaves
the SDK default unchanged, whereas Sunroom explicitly reports MIN_MODEM(1).

Related public sources (not proof of an S3/5.5.1 defect):
- ESPHome issue18149: original ESP32/ESP-IDF + ath10k missing-ACK disconnect report;
  reporter found an ESPHome downgrade helped, not a demonstrated PS-off fix:
  https://github.com/esphome/esphome/issues/18149
- ESP-IDF issue16096: ESP32-C6/OpenWrt broadcast/ARP loss with MIN_MODEM; original
  reporter found PS_NONE helped. Different chip and symptom; maintainers did not
  independently confirm an S3 reason34 fix:
  https://github.com/espressif/esp-idf/issues/16096
- OpenWrt FAQ documents disassoc_low_ack0 workaround; this disables eviction, not
  repairs missing frames, and is NOT applied to this network:
  https://openwrt.org/faq/disconnected_due_to_excessive_missing_acks
- Exact-version S3 guide documents default MIN_MODEM / optional NONE:
  https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32s3/api-guides/wifi.html

A Sunroom-only PS-off comparison remains a hypothesis test, not an established
fix. Keep Barn and AP settings unchanged to avoid invalidating the control.
Private comparison records: `barn-control-comparison.local.json`,
`barn-ap-control-current.local.json` under Sunroom recovery directory.

Private provenance/journals/captures remain under the Sunroom recovery pointer:
`wifi-diagnostics-release/`, `wifi-diagnostics-ota.execution.local.json`,
`wifi-diagnostics-first-capture.local.json`, `wifi-diagnostics-postcheck.local.json`.
Do not replay old flash/import/provision/OTA execution files. Barn was not updated.
