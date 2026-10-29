# Sunroom bounded single-AP / independent ACK observation — 2026-10-27

## Approval, isolation and final state

Jeremy approved the controlled trial and separately approved temporary verified
capture tools in the wired living-room AP's RAM. Sunroom's external circuit was
last reported disconnected, AC OFF, USB powered via the operator-selected port.
No GPIO arming/output test, serial open, physical reset, credential rewrite,
permanent AP pin, router package/service installation, channel or backhaul change.
Barn was untouched.

**Final deployment is the known PS_OFF baseline**, ELF
`d954bd43e51fd0943d18b8e6dff2ca3ee3f02d8689bac3a340f7142293e7202b`,
healthy/valid with eight definitions/layout/Seattle clock retained and GPIO
inactive/unarmed. Temporary trial image is NOT left deployed. Follow-up GETs
retained the same restored boot and PS_NONE0; five initial disconnects then Deco.

## Trial implementation and tests

`wifi_ap_trial.{c,h}` is default OFF in shared Kconfig/defaults. Enabled ONLY in a
private encrypted-vault build with the primary OpenWrt AP BSSID. No identifiers in
public source, no credentials in build options. Original station config is copied
in RAM; `bssid_set`/BSSID temporarily overridden. After a nominal20s deadline
(network polling plus SDK stop latency yielded restart ~21.4s), checked Wi-Fi
stop/set-original/start restores exact original config. No NVS writes.

Network health heartbeat withheld while pending: errors abort before pending-image
health validation, preserving OTA rollback. USB arm rejected in trial firmware;
matching saved-arm startup rejected before GPIO start. Pending trial also blocks
profile/manual/time mutations, USB provision and OTA fences. It repeats on reboot,
so a second deliberate guarded upload restored the original frozen baseline.

Actual C helper host tests cover default-off no-op, deadline/wrap, exact original
restore, each stop/set/start failure holding pending, bad/all-zero/multicast BSSID,
heartbeat/arming/shared-default source guards. Ring/JSON, power policy, actual
backend/profile/commit, 25 uploader and eight release regressions passed. Controller
build passed; selftest/stall/rollback injection OFF.

Temporary image956,528 bytes; image SHA256
`a474531f5deb26bf3eb9746b1c71ec1009e09c400c29f382c7004b356aae655e`;
ELF `539802fde8ec2f55c6a12e04280c02fef73437540affb1d49876f7799cdb4931`.
Source/SDK hashes and identity-bearing artifacts reside only in the private vault.

## Observer and execution

Independent observer: living-room wired WHW03 v1, monitoring channel1 while its
ordinary AP continues on channel1/HT20. Target AP: primary MX; no monitor setup
on its custom ath11k driver. Observer advertised monitor support, ~383MiB available
RAM. Signed OpenWrt24.10.4 ARMv7 metadata verified by its existing usign trust keys;
tcpdump-mini4.99.5 and libpcap1.10.5 package SHA256 values checked. Only selected
ELFs staged in a root-private /tmp directory; NO package scripts/install run.

`home-network/scripts/garden-wifi-observer.py`: unique absent monitor name,
channel/memory guards, owner tag, HUP-resistant170s cleanup timer armed before
interface creation, bounded140s/50k-packet/192-byte-snapshot capture over SSH into
the unlocked vault. Interface tagged via writable kernel ifalias attribute because
ip-tiny lacks alias syntax. Initial attempt caught that syntax limitation BEFORE
any upload; zero upload counts and complete cleanup verified. It was retired;
new attempt used DISTINCT plan/capture/journals, not an uncertain upload replay.

Successful attempt: independent radiotap header verified before ONE trial OTA;
expected healthy/valid new slot, auto config restored, unarmed/profile retained.
ONE separately journaled baseline-restoration OTA then confirmed the old known
image in the other slot. No fallback/unfenced upload or settings restore. Both
uploads preserve exact identity/fence/config/clock and no-replay protections.

Observer interface and staged tools removed. All recorded timer/capture PIDs
absent, no temporary monitor remaining, AP service ENABLED, network/wireless
configuration hashes unchanged. No boot service/persistent configuration changes.

## On-air result and limits

During two fixed-primary attempts (~boot+1.45s and+7.40s), the observer saw:

1. Sunroom open-system authentication request, cleanly decoded at ~-52dBm.
2. An ACK addressed to Sunroom soon afterward (ACK has no transmitter address;
   source association is timing/context inference).
3. Primary AP authentication SUCCESS response: algorithm0, transaction2, status0,
   matching AP BSSID, rate6Mbps, decoded at ~-54..-55dBm.
4. Each response repeated three times with retry flag/same sequence number.
5. No corresponding ACK addressed to primary or Sunroom association request seen
   in those exchanges. ESP reports failed attempts/reasons4/205, no link-up.

After deadline, auto selection resumed; Deco associated ~57.76s/IP58.80s.
A transient SDK connect-busy event followed restart; recovery completed normally.
No claim that all attempts used reason7 or reached WPA/DHCP. This is an earlier
open-auth exchange than the previously observed WPA-success/reason34 drop.

This independently confirms that AP success replies were actually transmitted
and retried, not merely described by a log. It supports a reception/ACK/state-
handling problem, not wrong credentials or Lua rules. It does NOT prove a broken
ESP radio or establish which end lost/misprocessed a frame. Observer decoding is
not proof of Sunroom decoding; missing capture is not proof of RF absence. Captured
FCS wasn't included; don't claim independently CRC-verified frames. Kernel reports
zero queue drops, but that is not a guarantee of complete over-air reception.

## Capture-filter limitation / privacy minimization

The initial -F stdin pipe was treated as a zero-sized file by this tcpdump build,
so the requested filter did not apply. Broader bounded radio capture existed ONLY
inside the encrypted owner-only vault; no unrelated payloads printed/shared.
Unrelated frames were then removed there: only176 station-relevant packets/ACKs
to target AP remain (~23KiB). Original and filtered digests/counts are recorded;
the original broader capture was replaced, not copied elsewhere. The offline
analysis retains target-frame metadata, not unrelated addresses/payloads.

Observer source now uses a regular root-only RAM filter file and deletes it in
normal/fuse cleanup. That follow-up filter fix is not yet router-revalidated; no
second capture/third firmware experiment was run merely to test it. Future use
must verify actual filtering, not assume a valid capture header proves it.

## Next investigative choice

Prefer a coordinated known-good spare comparison in the same location/cable/
antenna setup, or a short-range test near a known AP, before guessing more global
router settings. Current board/local RF/interoperability remain possible; Barn
is a working but differently located control, not a matched experiment. No such
further physical or network experiment is authorized by this completed run.

## Spare comparison — first OpenWrt join and five-minute observation passed

Jeremy connected a separate ESP32-S3 on Drallion and confirmed BOTH boards have
no external circuit attached (USB only). Read-only enumeration distinguished
production Sunroom from the new spare before any serial open. Initial unprivileged
attempt stopped on permission denial before opening; existing sudo access then
identified S3/16MiB/security disabled without host/group/udev changes.

Spare full16MiB original streamed directly into encrypted vault, independently
matched device full-range MD5 and shelf SHA/MD5 (440.26s). No raw backup/settings
written to Drallion. Original restore not exercised. A purpose-specific first-flash
worker excludes BOTH production chip identities, requires verified backup, checks
current full-flash MD5 against it before erase, validates exact geometry/security/
artifact hashes, then one same-handle erase/write/verify/reset. Six offline fake-
SDK/PTY tests cover success and identity/backup/security/production/artifact gates.

Spare received the EXACT restored Sunroom PS_OFF app, not temporary AP-trial image;
matching16MiB layout/bootloader/initial OTA data. All write/digest checks completed.
First native-USB reset selected ROM `DOWNLOAD(USB/UART0)`, `waiting for download`,
not application boot. This alone was NOT a Wi-Fi result and does not prove original
Sunroom HW-001 cause. Reader closed, port-owner check empty and own public firmware
staging removed. NEVER replay erase/write due to this reset.

Jeremy then power-cycled ONLY spare USB. Fresh USB inspection confirmed expected
ELF, healthy/valid, GPIO inactive/unarmed, PS0, credentials absent. Exactly ONE
credential provision acknowledged, using recovered credentials matched in memory
to Sunroom's current network; secrets entered Drallion process memory/target NVS,
not remote files or arguments. NO profile import/patch, relay/clock/hostname/arm
mutation. Spare retains factory `garden-bench`, one memory-only relay/manual clock.
It is a temporary diagnostic controller, not a Garden production list entry.

Spare first attempt: station start5797ms, connect6354ms, tenant-a association6489ms,
IP11665ms, reported RSSI-63dBm, channel1, PS0, zero disconnects. Independent strict-
key tenant-a hostapd/iw read confirmed authorized/authenticated/associated,2412MHz,
station signal-61dBm,1 TX retry/1 TX failure, connected347s at that query. Only
spare's record retained; other client metadata discarded in process memory.
Six LAN samples over300.17s (0/30/75/150/225/300) stayed on SAME AP and SAME boot
as provisioning, healthy/valid/unarmed/PS0, disconnect count0 throughout, four
untruncated diagnostic events (no failed join/disconnect). Sunroom separately still
healthy/unarmed/PS0 on Deco channel3, not reset or mutated. Barn/router untouched.

This narrows suspicion toward Sunroom-specific board/antenna/local RF/power OR
persisted station/NVS/PHY-calibration state, not a universal S3/IDF/OpenWrt failure.
It is NOT a board-defect proof: exact antenna/position/cable/port equivalence was
not established; factory profile and fresh NVS differ, and repeated-startup/long-
term reliability is untested. Coordinate further controlled swaps; no automatic
flash/reset, production profile copying, GPIO activation or network changes.

New timestamped spare recovery directory is linked by Sunroom's private
`spare-comparison-current.local.json`; its backup/flash events/checkpoint retain
exact identity/geometry/artifacts/stages. No production GPIO or network change.

Private evidence under Sunroom recovery pointer: single-ap2-controlled execution,
separate trial/baseline-restore OTA journals, observer plan/log/filtered pcap,
analysis/minimization, final postcheck and process-cleanup records. Original failed
observer attempt retained with verified zero uploads. Never replay execution files.
