# Reliability checkpoint — 2026-10-14 (bare spare only)

No live controller, relay module, contact or actual sensor was exercised. The
normal firmware is memory-only, unarmed, locally healthy/valid; controller images
only compile. No phone publish, commit/push, service/network/trust changes.

## Idle/burst observations

`scripts/test_idle_soak.py` uses single-attempt four-second GETs with silence gaps
0/1/5/15/30/60 seconds between diagnostic bursts. It checks boot/image/revision,
health/progress and memory-only identity; reports allowlisted latency, heap, RSSI,
disconnect/reset/task counters. It never stores profiles, labels, IP or SSID. A
failed request is recorded rather than retried; a separate bounded TCP handshake
can help distinguish transport from HTTP behavior. Initial Bench identity checks
alone retain their explicitly logged read-only verification retries.

The first run used 600 seconds and completed 210 requests, zero failures:

- Maximum 0.2417s, median 0.02405s, p95 0.1165s.
- Free heap first 193,236 / last 193,264; observed 191,240..193,588.
- RSSI -48 throughout returned samples; no disconnect-count increase.
- Same healthy boot/image/edit revision, final GPIO absent/inactive/unarmed.
- No reset, upload, input/profile mutation or Wi-Fi reconfiguration issued.

This run completed before installing the guarded-OTA extension. The source's
aggregate heap/RSSI summary was added while it ran; those numbers were derived
offline from its immutable raw samples, not represented as original live output.
A subsequent five-second smoke of the finalized report/summary path passed 48
reads with no failures on the guarded firmware. Reports are local temporary
sanitized JSON, created mode0600 without overwrite/symlink following; no server
or phone deployment. Six offline unit tests cover single attempts, privacy,
identity/config drift and report handling.

The tool bounds a run to 5..3600 seconds, with final verification potentially
extending the duration by 40s. Usage:

```sh
python3 scripts/test_idle_soak.py SPARE_IP --seconds 600 \
  --confirm-memory-only-spare --report /tmp/NEW-REPORT.json
python3 scripts/test_idle_soak_unit.py
```

The final version also flags gross retained heap loss (>16KiB) or <32KiB sampled
headroom. These broad guards and short heap samples are not leak proof.

## Load/adversarial observations

A 60-second two-worker HTTP run completed 1,541 requests with zero failures and
maximum 0.086s response. Slow-body 408, large-declaration 413/close, runtime health
and same-boot/config/output isolation passed. Sampled heap 190,996 -> 192,540.
The expanded mix including atomic edit snapshots and OTA-fence GETs then passed
1,450 requests/60s, zero failures, maximum 0.173s. Sampled heap 191,248 -> 192,828.
Bounded slow-body/oversize handling and same-boot/profile/output isolation passed.

New OTA reservation/stale-token/abort/USB-gate tests and full fenced update passed;
see GUARDED_OTA.md. A long USB test RPC initially lost its reply during initial
flash erase; read-only inspection found the original healthy configuration.
Waiting for receive-loop phase before long test RPCs passes. This is evidence of
a transport/timing caveat, not permission to retry an uncertain mutation.

## What this does NOT establish

- Earlier intermittent four-second HTTP timeouts remain unresolved, not disproven
  by ten clean minutes. No fix to radio power saving, TCP, AP or Wi-Fi settings is
  inferred/applied. Need much longer idle/load captures and correlation across
  target/client/transport. Heartbeats do not establish HTTP reachability.
- Zero disconnects is not an AP-loss/reassociation/reconnect test. Existing reset/
  OTA tests verify reconnection after reboot; deliberate AP-loss/reconnect and
  extended outage/recovery remain to test without changing shared infrastructure.
- No physical power interruption/brownout or module-contact/startup test here.
  Those are attended hardware gates, not substitutes for software resets.
- Neither shelf nor Drallion exposed an available adb command during this check.
  Actual Android rendering, keyboard/blur/navigation, mDNS and Capacitor plugin
  behavior need a coordinated phone sync/test. VM/fetch tests are not that proof.
- Full live backups, intended timezone/policy and controller commissioning/update
  execution/recovery review remain prerequisites to live migration. Read-only
  release audit is available; it never uploads/resets/arms.
