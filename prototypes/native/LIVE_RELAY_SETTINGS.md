# Live relay settings and lights-only remote OTA — 2026-10-26

## Later extension: live switch inputs, 2026-10-29

[LIVE_SWITCH_INPUTS.md](LIVE_SWITCH_INPUTS.md) adds a bounded all-manual/current/
startup-OFF path for switch input enable/remap/remove, retaining hardware enablement
and baselining the input without invented edges or relay writes. Original-target
Sunroom deployment confirmed; physical switch toggle pending. Ordinary active
relay-pin/clock/environmental sensor remapping remains blocked. A separate explicit
attended all-OFF OTA policy supports attached loads without falsely claiming
lights-only or equipment isolation. Historical scope below remains dated context.

## Explicit scope

Jeremy reported only lights connected (no power equipment), accepted that settings
may switch a relay, and requested removal of the live-settings restriction plus
remote Wi-Fi OTA. This supersedes the earlier main-OFF/bare-board requirement for
THIS lights-only maintenance session. It does not authorize firmware changes on
Sunroom2, USB access, pin remapping, other loads or future power-equipment use.
Reassess this policy before attaching equipment beyond lights.

## Firmware behavior

`/api/config` advertises `live_relay_settings:true`. Active controllers allow
`isInverted`, `defaultValue`, and `defaultAuto` edits through the existing narrow
revision/boot-guarded patch API. Labels/rules/current AUTO remain editable.

- Polarity edits retain the logical command and immediately write its NEW electrical
  interpretation on the same pin. This can switch the physical light. Both HAL and
  backend publish the new polarity/command only after a successful GPIO write.
- Startup defaults do NOT change current value/AUTO; they take effect next boot.
- Pin count/order/mapping, input ownership, sensor mode and clock policy changes
  still reject while active. Removing those checks alone would leave the physical
  driver bound to old resources, not implement valid live remapping.
- The full `io_layout_hash` encoding and `arm_v1` format remain unchanged, preserving
  existing armed controller startup and rollback compatibility. A successful
  permitted live edit rebinds the already-active, coherently armed controller's
  record to its new full hash. It cannot arm inactive GPIO or cancel pending
  explicit disarm. Initial activation is still USB-only.
- Profile and updated arm record are two NVS keys, NOT an atomic power-fail
  transaction. Mixed old/new keys fail closed on reboot by exact hash mismatch;
  availability across a physical cut is not proven. Reported rebind persistence
  failure latches `persistence_uncertain`, blocks further edits/arming/OTA, and
  requires inspection rather than retry. No GPIO write precedes persistence.
- `outputs_applied:false` or persistence uncertainty also blocks an OTA fence.
  A GPIO failure may leave a partial physical batch; no atomic contact claim.
- Schema, partition table, project/contract and initial arm phrase are unchanged.

## Remote OTA execution policy

The installed Barn server already supported coherent armed OTA. The old uploader
policy—not the server—required bare/unarmed controllers. `controller_ota.py` keeps
that default and adds an explicit alternative:

```text
--apply --maintenance-confirmed --lights-only-confirmed --remote-reboot-confirmed
```

Both lights-only/remote-reboot acknowledgements must be supplied together. Do NOT
claim bare-board isolation for connected lights. The owner accepts boot-default
light changes/interruption and that a failure can require physical recovery.
No assertion of nearby recovery access or unattended recovery is made.

All original private-target/image/security fences, two stable snapshots, Wi-Fi/
healthy-boot/slot/layout/config validation, exclusive new vault journal and single
POST/no replay remain. Active/armed coherence must hold before and after OTA;
pending arm/disarm is rejected even in lights mode. No USB, implicit arming,
settings restoration or unfenced fallback in the uploader. Clock and boot AUTO
are checked after reboot; current values intentionally can differ due to defaults.

## Verified Barn execution

Frozen diagnostic-free ESP32-S3 `relay-profile1` app: 953,152 bytes.
Image SHA256 `de61a1ac3e41675303da78f7340b7553618f3e84d683ed88b9b2c9ca7a9029bf`.
ELF SHA256 `5c6bcdfa9c95f429c2708649cec49bd7b93204a1fd3a188f5396525980565d82`.
Full original recovery backup rehashed/verified; frozen source hashes checked.

Exactly ONE fenced POST: confirmed new boot, ota_0 -> ota_1, expected full ELF,
healthy/valid, GPIO active/armed, unchanged configuration/layout, Wi-Fi and Seattle
network clock restored. No USB/reset intervention or arm/disarm. This is the first
Barn OTA and first lights-connected armed-controller OTA, not a cold-power,
brownout, physical-output continuity or rollback proof.

After successful verification, separately journaled one-shot requests restored
Overhead's pre-update ON state within its 08:00–20:00 window, enabled current and
startup AUTO, and changed Flood light(pin4) inversion true -> false with its
logical value/label retained. Both narrow setting edits read back with coherent
rebound arm/layout/fence, same healthy active boot, and no reported output,
cleanup, persistence or watchdog errors. Other seven rows untouched; existing
wall-switch logic and Seattle 08:00 ON / 20:00 OFF edges preserved.

Startup AUTO is saved but has NOT been exercised by a subsequent reboot. An
edge-only schedule does not catch up a missed 08:00 edge after a midday reboot;
startup logical OFF and `edge_no_catchup` remain intentional. Manual app control
disables current AUTO. Flood-light physical polarity confirmation awaits Jeremy;
software acknowledgment is not contact feedback.

## Tests / UI boundary

- Host C test compiles the REAL backend, profile normalization, HAL polarity
  function and runtime commit body against fake GPIO/NVS. Tests live polarity,
  startup-default rebinding, failures at both NVS keys/commit, sticky uncertainty,
  pending-disarm refusal, pin-remap refusal and upload reservation. No hardware.
- Controller startup backend selftests exercise polarity success/failure and
  compatibility without physical outputs. Host execution passes too.
- 21 fake uploader tests (including active lights success, lost ack/no replay,
  activation loss, pending disarm, identity/config rejection), 8 release tests,
  5 USB tests and host serial framing tests pass; controller build passes.
- Existing Garden native editor may still lock polarity/default checkboxes while
  active until it consumes `live_relay_settings`. No Garden/phone publication is
  part of this firmware OTA. Manual ON/OFF app functionality remains unchanged.

Private image/sdkconfig/source manifest, raw snapshots, identities and journals
remain in the encrypted backup vault. Never restore the older production profile
blindly: it predates the requested 20:00 OFF schedule and subsequent app labels.
