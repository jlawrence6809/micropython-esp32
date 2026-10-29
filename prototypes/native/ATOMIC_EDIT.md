# Atomic application editing (profile v1, unchanged storage/OTA contracts)

**2026-10-26:** New Barn firmware advertises `live_relay_settings:true`. Polarity
and startup defaults now support active edits with coherent arm rebinding; pin/
input/clock resource changes remain blocked. See LIVE_RELAY_SETTINGS.md for
persistence/failure semantics and explicit lights-only scope. Earlier layout-lock
statements below describe older firmware; clients must capability-gate the unlock.

`GET /api/config` advertises `atomic_profile_edit:true`. Older native firmware
without it must remain read-only in the new editor; never fall back to whole-array
writes. No authentication was added: revision/boot checks prevent accidental stale
updates, not unauthorized trusted-LAN access.

## Protocol

`GET /api/profile/edit` returns the credential-free canonical `profile`, an opaque
64-hex `revision`, `boot_id`, and existing OTA health/image metadata. It performs no
writes or GPIO operations. POST `/api/profile/patch` requires exactly:

```json
{
  "expected_revision": "<revision from edit snapshot>",
  "expected_boot_id": "<boot_id from edit snapshot>",
  "changes": {
    "relay_update": {"pin": 4, "label": "Lights", "changes": {"auto": true}}
  }
}
```

Allowed `changes` keys:

- `hostname`, `timezone`, `clock_source`: same types/limits as profile v1.
- `sensor_pins`: a nonempty partial object of the existing six pin fields. Merged
  into the current map, then validated for types, collisions, complete I²C pair and
  unsupported sensors. This does not enable sensor acquisition or GPIO.
- `relay_update`: required current `pin`/`label` identity and nonempty `changes`.
  Fields: pin, label, rule, auto, isInverted, defaultValue, defaultAuto.
- `relay_add`: exactly the six configuration fields pin, label, rule, isInverted,
  defaultValue, defaultAuto. Initial value/auto derive from the defaults.
- `relay_remove`: current pin/label identity.

At most one relay operation per patch. Unknown/duplicate keys, missing identities,
current `value` edits and arbitrary arming fields are rejected. Manual value
commands continue to use `/api/relays/control` and disable AUTO. Syntax/correctness
of arbitrary Lua is not guaranteed by profile normalization; Garden evaluates the
rule against the current snapshot before autosaving it.

## Atomicity and conflict rules

Dispatch already owns the runtime mutex. It compares boot/revision, merges **only
intentional changes into the current owned profile**, validates the complete result,
then invokes the same single-NVS-blob commit path. Existing unrelated values/auto
are never copied from the caller's old snapshot. Physical writes remain after
successful persistence, with existing last-successful-value/error semantics.

The revision hashes ordered canonical configuration (excluding current relay
`value` and transient diagnostics), plus an in-RAM explicit-commit generation.
Normal automation changes do not invalidate it. Every successful explicit commit,
including manual commands/no-ops through older endpoints, increments generation.
USB credential and arm/disarm commits now also conservatively invalidate it,
without exposing credentials; see GUARDED_OTA.md.
This prevents an old AUTO edit from silently overriding a newer manual command,
even when its resulting config/value happens to look identical. Boot IDs prevent
cross-reboot edits; generation need not be stored in flash. This is not an event
history or durable transaction ID.

- 400: invalid patch; no configuration adoption/output application.
- 409: stale revision/reboot or forbidden active layout change; inspect/reload.
- 503: not yet locally validated; no persistent change.
- Storage/allocation failures follow existing failure/uncertain-completion rules.
- Success returns the next `revision`, `restart_required`, `outputs_applied` and
  any output warning. Missing reply/revision is not proof that nothing happened.

No automatic mutation replay or silent conflict rebase. NVS/power-loss uncertainty
still requires inspection; physical power-cut durability is not proven here.
Active GPIO still rejects pin, polarity, boot-default, input, clock-source/timezone
changes through the layout fingerprint. Labels/rules/current AUTO can change
without remapping pins or resetting a valid clock baseline. GPIO arming stays
separate, USB-only, chip/layout bound, and deferred until reboot.

## Garden

Native editors autosave scalar fields on change, validate/save Lua on blur, and
serialize requests against only their own acknowledged revisions. Later queued
edits stop after any rejection, missing response or partial-output warning. A new
page closes queued-but-not-started work; already in-flight completion may remain
uncertain. Device addresses are frozen across asynchronous checks/queued writes.
Field-specific draft/error messages are kept separate from other saved fields.
Creation/deletion remain explicit Add/Delete actions, not Save buttons.

Unsupported/older firmware stays read-only. Native UI cannot arm GPIO, provision
Wi-Fi, reboot, or upload firmware. Actual phone rendering/plugin behavior and
production commissioning/update/recovery tooling still need review/testing.

## Coverage and limits

- Pure boot tests: revisions ignore runtime values, include explicit generation,
  merge preservation, type/key/identity/collision rejection; label/AUTO edits keep
  layout hashes, pin changes alter them. No GPIO or storage in these helpers.
- `scripts/test_profile_edit.py`: actual RAM automation changes after a snapshot
  do not invalidate its revision and are preserved by later edits; explicit/manual
  no-ops do invalidate it; stale/boot/invalid rejection, add/update/remove/AUTO and
  input changes. Restores original profile/switch input.
- `scripts/test_profile.py`: pending-boot patch rejection plus actual reboot nonce
  rejection, existing profile persistence/defaults and restoration.
- Garden Node VM tests: serialized requests/identity changes, no retries/rebase,
  pause/close, frozen address, mode/layout UI locks, field-change/rule-blur/pin-pair
  autosave, legacy/native separation. Not a real browser.
- Garden actual-HTTP smoke: manual/AUTO, label/rule, hostname, timezone/source,
  input reservation and output preservation, then full original-profile restore.

At this milestone, 24 Garden VM tests and the extended actual-HTTP smoke pass.
A 200-edit-snapshot read sample retained one revision/boot and sampled heap
193,212 -> 193,552 bytes; separate 200-evaluation USB sample 193,508 -> 193,528.
These are short observations, not leak or long-term network reliability proof.
Existing backend, profile/pending/reboot, engine, clock/DST and HTTP regressions
also pass. No phone publish, commit or push was performed.

All device tests use only the validated memory-only spare. Controller builds are
compile-only, never booted/armed; real GPIO startup/contacts remain unverified.
Optional actual sensors are deferred and do not block this relay-first scope.
