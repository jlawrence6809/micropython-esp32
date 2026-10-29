# Native USB setup, UART logging retained

**2026-10-28 target note:** the native USB/FIFO path below remains S3-only.
Original ESP32 builds compile the shared UART0 setup/reply/arming protocol without
that peripheral; an external3.3V-logic UART adapter is required. This extension
is compile/offline-tested, not hardware-tested: [ORIGINAL_ESP32.md](ORIGINAL_ESP32.md).

## Verified Barn milestone — 2026-10-20

Jeremy approved this enhancement while Barn remained laptop-USB-powered through
its native USB socket and equipment main power stayed OFF. No GPIO arm command.

The previous UART-only image booted correctly on native USB, but that socket was
only a secondary log output. `runtime.c` now accepts setup input on BOTH UART0 and
native USB JTAG/serial CDC, while preserving UART0 as primary logging console and
native USB as secondary log output. GPIO/rules/profile schema/arming logic and
`relay-profile1` contract are unchanged. Sunroom2 was NOT updated in this task.

Working application: 952,000 bytes, project `garden_native_probe`;
file SHA256 `d4bfc3f0a929777d7ef0775cf11daef5c57e5bdaac53ec9909896409abe821bd`;
ELF SHA256 `8511f243031db82d83e2346512e09d129243227ab2c8a13f3c54a72f1076dda3`.

- Exact chip/security/16MiB geometry and installed immutable image digests were
  checked before app-only replacement at `0x20000`.
- No full erase, bootloader/partition-table replacement or NVS write in this
  app-update step. Write + device-digest verification passed, native reset booted.
- Native USB GETs verified exact identity/full ELF, healthy valid boot, active
  task monitor/no timeout, factory profile and inactive/unarmed GPIO.
- A reviewed single-session restore imported all NINE Barn definitions/Lua/
  polarity/defaults and privately provisioned Wi-Fi, once each. Both mutations
  were acknowledged and read back; factory/unprovisioned preconditions checked.
  Wi-Fi connected; same healthy boot and inactive/unarmed GPIO confirmed.
- After closing USB, independent LAN GETs verified the same boot/chip/ELF, all
  nine definitions/layout, Wi-Fi and unarmed state.
- A later native session completed 12 profile GETs (maximum 0.055 seconds), an
  EXACT 12,288-byte valid GET (3.858 seconds), an oversized 12,400-byte invalid
  frame rejected with 400 (3.876 seconds), then fresh GETs. Same healthy boot,
  edit revision/layout and inactive/unarmed GPIO; no config/output mutation.

A subsequent native session was observed on a DIFFERENT boot from initial
restore. Later LAN checks match that session's healthy boot (349 seconds uptime,
175,516 bytes free heap at inspection), with all nine definitions and credentials
preserved and `barn` hostname ACTIVE/no pending restart. SDK reset reason 11 is
`ESP_RST_USB`, not a task-watchdog reset. The exact USB transition causing it was
not isolated. Thus persistence across an observed new boot IS verified; an
untouched cold-power/brownout recovery test is NOT.

Subsequently Jeremy removed USB and restored equipment power; LAN verified
healthy native Barn on circuit power, still inactive/unarmed. Physical overhead
lights ON despite API logical OFF is not feedback or proof of control. With
explicit Seattle approval, ONE guarded clock-only patch set LA/network; same
healthy boot, unchanged definitions/defaults/AUTO and synchronized valid PDT
schedule clock verified. No light/output/arm command sent. Old main-OFF isolation
is no longer assumed. Re-isolate before USB/electrical commissioning.

**Still pending:** clock patch persistence across another boot, physical outputs/
switches and Barn controller OTA. Sensors disabled. Zero ON boot defaults, one AUTO default do not authorize arming.

## Transport design

- ONE existing serial task, same watchdog lease/heartbeat ID; no extra unmonitored
  task, driver/ISR, console switch or GPIO setup.
- Separate `serial_frame` buffers for the two physical inputs. Each bounds input
  at 12,288 bytes + terminator. CR ignored, LF completes; overflow rejected only
  after LF and never truncated into a valid command. Buffers independently reset
  with volatile clearing, including credentials. Pure host C tests cover
  interleaving, exact limit, overflow/recovery, CRLF and clearing.
- Fair bounded per-transport polling and tick delay; UART uses existing driver.
  Native RX polls the S3 USB-serial-JTAG FIFO via the IDF HAL. Only this task may
  consume that native RX FIFO; do NOT install a competing native CDC input driver.
- Reply envelopes go ONLY to the originating physical port, never broadcast to
  another client's potentially identical request ID. Existing primary/secondary
  logs remain mirrored; stdout locking prevents frame/log interleaving.
- Both ports use the same existing request dispatch, healthy-boot/mutation/OTA
  reservation checks, and exact physical USB-only arming gates. This is NOT a LAN
  arming path. Arming on native USB was deliberately NOT tested/executed.
- USB host `Device` uses an eight-second write timeout as well as bounded reply
  reads. Eight seconds permits the maximum native frame's observed ~3.9-second
  transfer. Timeout/lost mutation replies remain uncertain: never replay/rebase.
  Use its normal read-only role/boot handshake before setup; an immediate manual
  no-handshake reopen lost one initial GET, BEFORE any mutation. Fresh factory/
  unprovisioned/healthy state was inspected before the later one-shot restore.

This implementation is tied to IDF5.5.1/S3 and the enabled secondary USB console
(`/dev/secondary`). Revalidate console/HAL/VFS behavior on any SDK upgrade. UART0
code/logging are retained and compiled; simultaneous physical dual-port clients
and post-change UART hardware operation were NOT commissioned on Barn.

## Development evidence / recovery boundaries

The first candidate used a nonblocking read on the SDK secondary VFS. In this
IDF version its read-availability function checks an uninstalled interrupt
backend's ring buffer, not raw FIFO, so no USB RX was consumed. The first app
was verified/booted but a GET-only test stalled its host write. That owned reader
was interrupted/released; no restore ran. The RX-fixed image above was then
explicitly built/frozen/staged and app-only written/verified, not blindly retried.
The first candidate is NOT the working release. Its frozen artifact/journals
remain preserved privately.

Never compare initial erased OTA-selection data against its post-boot contents
as if it were immutable. Bootloader/table/app are immutable here; OTA selection
and NVS are mutable. Exact boot/slot/valid health must be verified independently.

`remote_native_app_update.py` is for this isolated factory/unarmed bring-up ONLY,
not normal active-output updates. It gates exact installed/staged digests, writes
one app, verifies and resets once; no full erase/retry/automatic recovery.
Its five fake tests cover boundaries/failures. Existing release/uploader and
resume tests remain offline; raw logs, identity/settings, full original backup,
release/source hashes and one-shot journals remain owner-only in the unlocked
vault. No raw flash/config/credential file was written on Drallion, only public
firmware/tools in a temporary directory. All reader sessions closed.

For subsequent images `controller_ota.py` remains attended UNARMED-only and
requires no pending hostname/boot/arm state. Treat ANY USB open as a potential
restart requiring attended/isolation approval; prefer LAN for ordinary inspection
before routine updates; name activation is now verified, but other gates remain.
[CONTROLLER_OTA.md](CONTROLLER_OTA.md),
[BARN_BRINGUP.md](BARN_BRINGUP.md), [COMMISSIONING.md](COMMISSIONING.md) and
[KNOWN_ISSUES.md](KNOWN_ISSUES.md) retain the other commissioning/recovery gates.
Native USB boot success does NOT diagnose/fix the CH340/RET path or imply reliable
unattended power/brownout recovery. No commit/push, Garden publication, live relay
operation or sensor commissioning was performed.
