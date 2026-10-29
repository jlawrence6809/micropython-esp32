# Guarded OTA reservation (public consistency checks, not authentication)

The server closes the configuration/arming TOCTOU gap discovered while adding
controller update tooling. Trusted-LAN/no-auth policy is unchanged. Subsequently,
Sunroom2 was migrated while physically isolated and one attended UNARMED Wi-Fi
update/reboot was verified on 2026-10-16; see [CONTROLLER_OTA.md](CONTROLLER_OTA.md).
GPIO has never been armed; Barn is unchanged. Active-output updates and physical
commissioning remain separate gates.

## Protocol and lock scope

- `GET /api/config` advertises `guarded_ota:true`.
- `GET /api/ota/fence` returns an opaque 64-hex `fence` for a healthy valid boot,
  unchanged boot selection, successful I/O cleanup, no deferred hostname and
  coherent current-GPIO/saved-arm state. Pending arm/disarm/hostname activation
  must be handled separately, not via an incidental OTA reboot. During upload the
  fence getter rejects with 409.
- The token hashes a domain/version prefix, chip ID, boot nonce, layout, explicit
  edit revision, full running ELF and current active/saved armed flags. Normal
  automation values are excluded. Explicit successful profile/manual commits,
  credential provisioning and USB arm/disarm (including no-ops) invalidate it.
  Credentials are never included/exposed. It is not a secret or authentication.
- POST `/api/ota/upload` accepts `X-Garden-OTA-Fence` in addition to the existing
  mandatory `X-Firmware-SHA256`. **Controller builds require a matching token**.
  Bench builds retain unfenced compatibility; supplied bench tokens are checked.
  Pure boot tests exercise mandatory-controller/optional-bench acceptance and
  identity/boot/layout/revision/image/arming invalidation.
- Upload atomically claims `uploading` before taking the runtime mutex briefly to
  check the fence/current health. Already-started commits finish before the check;
  changed state rejects before any image flash write. Later profile/manual/time
  commits, USB arming/disarming and credential provisioning return 503 without
  application while the reservation is held. Ordinary automation continues.
- The runtime mutex is **not** held across receiving, hashing or writing the image.
  Image/project/chip/contract/digest checks remain. On any staging failure/abort,
  the reservation is released and boot selection remains unchanged. On success,
  it stays held across boot selection and the delayed reboot; no final write gap.
- Small rejection replies get a bounded 16KiB/250ms cooperative discard before
  closing, rather than an unbounded image purge or reuse of unread image bytes as
  another request. One blocking recv may extend that budget by its socket timeout.
  Large/failed streams can still lose replies: inspect, never auto-replay.

A valid reviewed token can become stale before reaching the device; that is a
409, not permission to automatically read/rebase/retry. Unknown NVS completion
still needs operator inspection/reconciliation before another maintenance action.
This is not a durable operation log or proof of physical power-cut durability.

## Tool boundary

`scripts/ota.py ... --guarded` exercises successful fenced updates **only on the
verified development bench**. Existing bench tools still refuse controllers,
even unarmed ones. `scripts/controller_release.py` validates controller binaries
offline or GET-audits an independently identified controller, checking the new
capability/token and stable metadata across two snapshots. It still has no
upload/reset/arm action. Separate `scripts/controller_ota.py` now supports one-shot
attended BARE/UNARMED controller execution with mandatory fences, exact identity,
new private journal, no redirects/replay/fallback and full post-boot verification.
It deliberately refuses active-output controllers. One actual Sunroom2 update
passed; see CONTROLLER_OTA.md. Controller recovery/physical-output/update policy
still needs applicable review; see COMMISSIONING.md.

## Verified on the disconnected normal spare

- Successful fenced OTA: next slot, changed boot, expected full ELF, valid/healthy
  image and preserved configuration/Wi-Fi.
- `scripts/test_ota_fence.py`: no-op profile commit invalidates the old token;
  stale/wrong token rejected before selection; partial correct-token stream holds
  the reservation; eight USB profile/manual/config/time/arm/disarm/credential writes
  reject; abort releases it; same healthy boot/profile and later explicit writes
  work again. This writes/aborts only an inactive-slot partial image.
- Initial long USB negative-test RPC during flash erase lost its response. Read-only
  inspection confirmed healthy original configuration. The test now waits for
  `image_streaming:true` (after begin/erase and prefix write) before long RPCs, and
  passes. Non-IRAM UART RX loss during erase is a suspected cause, not proven by
  an electrical trace. This does not justify retrying uncertain mutations.
- `image_streaming` is diagnostic phase metadata, not a health guarantee. The
  underlying SDK can delay tasks during flash operations; this is not hard-real-
  time output control and remains a maintenance-window operation.
- Existing malformed/project/contract/digest/integrity/interruption rejection,
  profile/pending/atomic-edit and HTTP stress regressions pass. Header-rejection
  fixtures use small prefixes so replies are not obscured by large unread bodies.

USB arming requests now carry the expected boot nonce into the device-side locked
check as well as the CLI preflight, closing a separate check-to-command reboot
race. Missing/stale boot IDs reject before any arming write. This controller-only
branch remains compile-reviewed, not exercised on actual GPIO hardware.

The bench coverage above originally preceded controller execution. A subsequent
Sunroom2 initial install and one UNARMED controller Wi-Fi update are now verified;
no controller GPIO diagnostic/arming/contact test was performed. Application task
progress is not an independent hardware watchdog, contact feedback or electrical
safety proof. Real output/power/brownout and equipment recovery need attended tests.
