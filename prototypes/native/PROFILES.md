# Application profiles and provisioning

Verified on the disconnected spare, 2026-10-14. No GPIO diagnostic or live-unit
operation was performed in this milestone. Normal firmware remains memory-only.

Subsequent guarded GPIO-backend integration is documented in
[GPIO_BACKEND.md](GPIO_BACKEND.md); its controller build has only been compiled.

## Profile v1

`GET /api/profile` exports a canonical JSON object with exactly these fields:

- `format_version`: 1
- `hostname`: lower-case DNS label, 1..63 ASCII characters, no leading/trailing '-'
- `relays`: validated unique pins/labels, Lua source and five boolean state/default fields
- `sensor_pins`: complete six-field pin map, -1 for disabled inputs
- `timezone`: null (unconfirmed), UTC, America/Los_Angeles or America/New_York
- `clock_source`: manual or network
- `schedule_policy`: edge_no_catchup
- `sensors_enabled`: false for the relay-first release

Input assignments reserve pins and detect conflicts; they do not configure GPIO.
I2C pins may be reserved together even without a sensor attached. Unsupported
DS18B20/photo input assignments and sensor activation are rejected, not pretended
functional. Arbitrary top-level fields (including `armed`) are rejected. Relay
properties outside the known eight configuration fields are stripped on export/
persistence; diagnostics and unrelated metadata are not part of configuration.
Duplicate required relay keys are rejected.

Validation covers schema, bounds and pin ownership, not correctness of arbitrary
Lua logic. Rules still run under the existing bounded evaluator, with errors
holding outputs. Use rule validation and deterministic engine traces as well.

## Interfaces

- `POST /api/profile/validate`: accepts a full profile; pure validation, no settings,
  clock, output model, flash or hostname changes.
- `POST /api/profile/import`: validates/canonicalizes, prepares the memory output
  model and saves one authoritative NVS string (`bench/profile_v1`). No GPIO can
  be activated through this endpoint. Only returns success after persistence.
- Existing relay configuration/manual-control and timezone APIs now update that
  same profile, so later updates do not silently discard identity/input settings.
- Persistent writes return 503 while local OTA boot health is pending. Pure reads,
  rule tests and profile validation remain available. USB tests poll read-only
  health before issuing mutations; uncertain writes are never automatically replayed.

Hostname changes are deferred until reboot: `/api/config` reports configured
`hostname`, `active_hostname`, `restart_required`, and immutable bench role.
Timezone and persisted clock-source selection apply to the memory-only engine.
The bench clock-source endpoint remains a volatile override; full import/reboot
restores the persisted choice. Ordinary relay/timezone updates preserve that
volatile override unless the persisted source actually changes.

Import initially applies `value` and `auto` to the RAM model. Reboot restores
`defaultValue` and `defaultAuto`, not the momentary state in an export. All relays
still share one input snapshot per cycle.

## Storage, compatibility and recovery

An absent profile is read-only migrated in RAM from legacy relay/timezone keys;
first successful settings write persists the full profile. Legacy keys are frozen,
not erased or mirrored with potentially non-atomic multi-key writes. Malformed,
unknown-version or oversized stored profiles fail closed, never silently replaced.

One stored blob avoids mixed identity/pin/timezone/relay revisions across reset.
This has not yet been physically power-cut tested. NVS/storage errors can leave
completion uncertain: do not blindly replay writes; inspect over HTTP/USB and
verify persisted state after a controlled reboot. Subsequent backend code blocks live layout changes and handles partial resource
initialization. Electrical startup/cleanup safety still requires attended tests.

Firmware uses app-version contract `native-profile1` (code identity remains the
full ELF SHA). OTA rejects images with a different contract, including pre-profile
images that would ignore current settings. Same-contract failed pending boots
still automatically roll back. Future incompatible schemas need a reviewed staged
migration/compatibility bridge, not merely changing the version string. Do not
install an old raw image as a workaround for the OTA check.

Profile exports intentionally exclude Wi-Fi credentials, raw NVS, firmware and
filesystem data. They are not a full device recovery backup. Initial live-device
backup/flash still requires an approved attended maintenance/recovery plan.

## CLI

```sh
python3 scripts/device_profile.py SPARE_IP export /PRIVATE_VAULT/spare.local.json
python3 scripts/device_profile.py SPARE_IP validate /PRIVATE_VAULT/spare.local.json
python3 scripts/device_profile.py SPARE_IP import /PRIVATE_VAULT/spare.local.json --apply
```

Exports require a gitignored `.local.json` filename, mode 0600, and a new path;
existing files and symlinks are not overwritten. Keep real profiles in the private
vault, not Git or chat. Import requires explicit `--apply`, waits for healthy boot,
and never retries an uncertain request. Profiles contain private labels/rules even
though Wi-Fi secrets are excluded.

## Verified results

- Complete profile import/export, hostname defer/reboot/restore, input-map and
  timezone/network-clock persistence; both inversion and boot-default semantics.
- Nine invalid-profile cases rejected with configuration unchanged; pending-boot
  profile/timezone/relay writes rejected before persistence.
- Original profile restored through verified USB, including active hostname;
  USB/HTTP boot IDs checked to ensure both paths target the same spare.
- CLI export/validate, 0600 permissions and no GPIO activation. Temporary export
  lived on `/dev/mapper/private-services` and was removed afterward.
- Shared-engine tests, USB regression, 85 snapshot/reference comparisons, both
  private relay profiles, 24 DST conversions, HTTP and pure I/O planning passed.
- Format/project/config-contract/digest/image-corruption/interrupted-upload tests
  passed. Rebuilt same-contract fault image rolled back; a subsequent normal OTA
  succeeded with the full application profile preserved.
- Normal image: 929,728 bytes. A short 200-validation heap sample was unchanged,
  202,876 -> 202,876 bytes; not a long-term leak/stability proof.

Reproduce the profile tests only on the verified simulated spare, using the IDF
Python environment with pyserial and authorized USB access:

```sh
python scripts/test_profile.py SPARE_IP
```

Garden actual-phone testing/publishing (atomic autosave now implemented; see
ATOMIC_EDIT.md), controller-safe commissioning/update tools,
extended adversarial/network testing and intermittent HTTP-timeout investigation
remain before hardware-test readiness. Continuous progress monitoring and initial
stall/stress tests now pass; see RUNTIME_WATCHDOG.md. Real-GPIO activation/resource lifecycle code is now
implemented but has only been exercised through a RAM driver. Sensors still do not block the first relay release.
