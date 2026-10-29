# Live switch-input settings — 2026-10-29

Jeremy approved replacing the routine USB disarm/configure/re-arm cycle for
switch-input edits. Implemented on the original-ESP32 Sunroom Relay_X8 by one
explicitly approved attended all-OFF LAN OTA, then one live GPIO18 input patch.
No initial arming bypass, no GPIO allowlist widening, no relay-pin remapping and
no claim of mains isolation or lights-only loads.

## What is allowed

The existing boot/revision-fenced `/api/profile/patch` accepts `sensor_pins`
`light_switch` and `reset_switch` enable/remap/remove, including exchanging the two
input pins, while hardware remains active. BOTH old and new profiles must have
EVERY relay `value`, `auto`, `defaultValue`, `defaultAuto` false. Actual backend
commands must also be OFF. Relay pins/order/count/polarity, clock/schedule policy,
environmental sensor pins/acquisition mode remain unchanged. Existing label/rule
edits remain possible; they do not enable AUTO. Original ESP32 strapping pins
5/12/15 cannot be newly selected as live inputs; normal target-specific pin,
resource-collision, health, persistence, cleanup, pending-disarm and OTA guards
remain in force. Remapping relay outputs is still a separate maintenance task.

Example shape (use freshly read revision/boot; do not replay on uncertainty):

```json
{
  "expected_revision": "<current 64-character revision>",
  "expected_boot_id": "<current 16-character boot ID>",
  "changes": {"sensor_pins": {"light_switch": 18}}
}
```

GPIO18-to-GND via an isolated voltage-free contact uses the existing hardware
driver's internal pull-up, closed-to-ground=true, 40ms debounce and bounded stable
baseline acquisition. No external 12V/mains allowed on GPIO. Board pad/lead voltage
and physical wiring are operator responsibilities; profile validation cannot
measure them. Environmental sensors can remain disabled. This configures an input,
not an automation rule: all relay AUTO flags remain OFF until separately requested.

## Transaction and failure behavior

`io_live_switch_settings_compatible()` verifies the bounded delta and all-OFF
conditions. `io_backend_reconfigure_switches()` touches input handles ONLY; it never
opens/closes/writes relays. Changed old input handles are closed before new ones
open. Failed open attempts are tracked/cleaned and old inputs restored; failed
cleanup or restoration is explicit, not a successful applied configuration.

Under the runtime mutex, stage inputs, sample and set BOTH current/previous switch
states to the stable baseline, without altering environmental/time baselines.
No invented switch edge. Persist the profile and its existing-device arm binding,
then publish the profile/revision. No relay write is needed in this input-only
commit. On NVS error restore old inputs/baseline if possible; mark persistence
uncertain and block subsequent mutation/OTA. On GPIO cleanup failure also mark
outputs unapplied. The two NVS keys are NOT power-fail atomic: a torn profile/arm
pair fails closed at boot by hash mismatch. This is failure containment, not a
physical power-loss proof. Initial hardware activation still requires the existing
explicit USB-bound approval; routine qualifying input changes preserve enablement.

## Attended all-OFF OTA

New executor alternative: `--all-relays-off-confirmed --remote-reboot-confirmed`
with `--maintenance-confirmed --apply`, selected chip/image, private expected-ID
target and NEW vault journal. Mutually exclusive with lights-only/equipment-OFF
policies. This truthfully allows attached equipment only when all current/AUTO/
boot defaults are OFF in both coherent preflight snapshots and after reboot.
Activation/config/identity/fence/health/clock guards unchanged; upload exactly once,
uncertainty followed only by GETs. No isolation or current-flow sensing implied.
The server reserves a consistency fence, not an authentication credential. Trusted
LAN/no-auth remains; no Internet exposure. Keep physical recovery available.

## Evidence and limits

Both-target real backend/profile/runtime commit host tests with fake GPIO/NVS
cover enable/remap/remove/swap, held-input baseline, unchanged time/environmental
baselines, all four OFF flags in old/new profiles, polarity/relay/sensor/strap
conflicts, pending disarm, partial GPIO open failure, remap rollback, cleanup
failure, each NVS failure point and failed rollback. Assert ZERO relay operations
for input transactions. Existing loader/profile/backend tests pass both targets;
32 uploader, 8 release and 11 original-target tests and compiler guards pass.
A hardware bench script invoked without its required environment failed during
local `serial` import before arguments/device access; it was NOT a hardware test.
No host-only test is represented as electrical/contact validation.

Original-target app965,808bytes SHA256
`c92871627cbda59b522f6546575ef6a26056d3111029411c08c47384101e3dfb`, ELF
`e481598cdad857b38b35afc586b1b3e1ff96b2fb0a0f42cfbd7ea88c15d70997`.
One all-OFF OTA switches ota_1 -> ota_0, expected new healthy/valid boot, Wi-Fi and
profile/labels/armed GPIO retained, all8 values/AUTO/defaults OFF. Then one live
`light_switch:-1 -> 18` patch succeeds WITHOUT reboot/UART/disarm, updates arm
binding, same healthy boot/all-OFF state. Four physical input samples read false
(open); operator toggle is still pending. No light rule enabled. No pin-change
reboot retention, cold-start, power-cut or contact proof yet.

Private first-board `live-switch-release-current.local.json` points to frozen
release, source hashes, tests, preflight/OTA/input-patch evidence. Checkpoint and
`current-reviewed-profile.local.json` are current. Earlier arm plans and OTA images
have stale layout/profile/ELF; NEVER replay them. Original stock backup retained.
Second Relay_X8 and active Barn unchanged. No Garden/phone publication or commits.
