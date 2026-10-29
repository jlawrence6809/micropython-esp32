# First release: relay controllers, not sensor expansion

Jeremy clarified the scope on 2026-10-14: Barn and Sunroom2 currently control
relay/light pins on schedules. Finish the software for those core functions first;
actual sensors can be attached later. Sensor hardware does **not** block this release.
Existing optional wall-switch behavior should remain compatible.

**2026-10-16 status:** Sunroom2's isolated initial native installation and private
profile/Wi-Fi restore are verified, but GPIO has never been armed and physical
commissioning remains outstanding. Jeremy explicitly deferred RET/reset
investigation; see [KNOWN_ISSUES.md](KNOWN_ISSUES.md). One attended UNARMED
controller Wi-Fi OTA/software reboot subsequently passed with configuration,
clock and health verified; see [CONTROLLER_OTA.md](CONTROLLER_OTA.md). This is not approval to
connect loads or skip the remaining clock, application and physical-I/O gates.

## Implemented and tested

- Native Wi-Fi/HTTP/NVS, bounded Lua rules, supported relay configuration/manual
  controls, OTA integrity validation/health confirmation/rollback.
- Private profile translation and 85 snapshot/reference comparisons.
- GPIO output and debounced-switch HAL components. Prior isolated spare tests
  verified GPIO4 levels, GPIO5 sampling and pin cleanup, not relay modules/wiring.
- Shared relay engine (`main/relay_engine.c`), used by the actual automation task
  and by deterministic trace tests. All outputs still use a memory-only writer.
- Explicit manual commands synchronize the output-level model; label-based manual
  control disables auto mode, matching the legacy control endpoint.
- Real synchronized clock can feed the same engine on the bench, only with an
  explicitly selected timezone. Unconfirmed/missing clock returns nil to rules.
- Writer errors preserve prior published logical state; subsequent attempts can
  recover. Rule failures similarly preserve state. Redundant on/off results do
  not issue repeated output writes.

## Clock semantics now exercised

The shared engine gives all relays the same snapshot and advances previous inputs
once per cycle. In network-clock mode it establishes a new time baseline after:

- Boot/first valid sync or recovery from an unavailable clock.
- Backward UTC/monotonic time, a gap greater than five seconds, or UTC/monotonic
  drift greater than two seconds.
- An inconsistent local-time delta, including DST/timezone changes.

The copied edge-based schedules therefore do not replay missed transitions after
those events. Normal threshold crossings still run; normal midnight progression
is continuous. This is not calendar-event deduplication, and custom Lua rules using
only current time can intentionally implement desired-state/catch-up behavior.
The original threshold comparisons themselves are unchanged (including their
existing midnight limitations). Current live thresholds are not at midnight or
within DST's repeated/skipped hour. Confirm intended boot/catch-up/timezone policy
before enabling real outputs; do not infer it from the inconsistent legacy clocks.

Whole-application identity/relay/input/time configuration provisioning is now
implemented and tested; see [PROFILES.md](PROFILES.md). It is a single authoritative
blob with strict validation, reboot defaults and OTA configuration-contract checks.
Wi-Fi credentials remain a separate USB provisioning concern, never an export field.

The GPIO backend and switch sampler are now connected behind separate firmware
and USB commissioning interlocks. Resource lifecycle/failure paths pass through a
RAM driver; the isolated Sunroom2 controller has now booted and restored its
profile/Wi-Fi, but has never been armed or electrically commissioned. See
[GPIO_BACKEND.md](GPIO_BACKEND.md). Pin ownership/layout locks and partial-write
state publication are implemented; electrical behavior remains unverified.

## Software still required before the hardware-test milestone

1. Test actual phone behavior and review/publish Garden changes. Native relay/AUTO,
   rule, hostname, clock and input editing now use boot/revision-checked atomic
   partial updates and serialized autosave; conflicts/unconfirmed writes pause
   without replay/rebase. VM and actual-HTTP spare tests pass; not published.
   See [ATOMIC_EDIT.md](ATOMIC_EDIT.md).
2. Finish controller commissioning/profile/update execution tooling and review
   recovery. Read-only release/image audits and COMMISSIONING.md are now available;
   mandatory controller OTA fencing/reservation is implemented, tested on the bare
   bench and compiled for controllers (GUARDED_OTA.md). Initial isolated Sunroom2
   USB/profile/Wi-Fi execution and one attended UNARMED controller OTA are
   verified. Active-output OTA execution and physical recovery remain gated.
3. Longer idle/reconnect/network/power testing, correlated investigation of
   intermittent HTTP read timeouts, and release review. Continuous task-progress
   monitoring, all-four-task stall recovery and initial adversarial HTTP tests now
   pass on the memory-only spare; see [RUNTIME_WATCHDOG.md](RUNTIME_WATCHDOG.md).
   Ten-minute idle/burst and expanded 60s-load runs also pass; earlier intermittent
   timeouts remain unresolved and AP-loss/power tests are not covered. See RELIABILITY.md.

Garden sync state was checked clean through an existing authenticated source-host
route before edits. No SSH trust, sync service, commit or deployment was changed.

Optional sensors must report unavailable, not simulated values, in a future real
controller mode. A missing AHT21 must not prevent relay-only startup or OTA health.
DS18B20/ADC expansion and actual AHT21 measurements can follow the first release.

## Hardware-test and deployment gates (later)

- Explicit user/operator coordination for actual relay/module/wiring, reset and
  power-loss checks. Do not equate RAM output levels with electrical verification.
- Confirm timezone/DST and boot/time-correction policy before real schedules run.
- Full live backup and attended initial-flash/recovery plan. Bootloader entry even
  for reading flash resets the controller, so it needs a maintenance window.
- Test one controller at a time. Sunroom2's physically isolated initial USB
  migration was explicitly authorized; Barn changes and live-equipment GPIO
  activation remain separate approval gates.

## Current software-only test interfaces

- `GET /api/engine/status`: backend, commanded levels, counters, clock source/policy.
- `GET /api/io/status`: compiled/active mode, layout/chip binding, arming state.
- `GET /api/watchdog/status`: continuous progress monitor, task ages/reset masks.
- `POST /api/bench/backend-selftest`: pure RAM-driver lifecycle/fault tests; no GPIO.
- `POST /api/bench/engine-run`: execute a private copy of valid relays against up
  to 16 frames/64 relay outcomes, with optional injected clock/write failures.
  Always uses a local RAM backend, never changes global config/inputs or NVS.
  Cooperatively bounded to 500 ms between frames, plus any in-progress bounded
  rule batch; this is not a hard real-time limit.
- `POST /api/bench/clock-source` with `source: manual|network`: bench-only, volatile,
  reset time baseline. Default after reboot is manual. Network mode refuses manual
  timestamp injection and still never enables GPIO.
- `GET /api/profile`, `POST /api/profile/validate`, `POST /api/profile/import`:
  canonical application configuration export, pure validation and explicit import.
  No GPIO activation; persistent writes wait for validated boot health.
- `POST /api/relays/control` with `label` and boolean `state`: persist a manual
  command and disable auto for that relay. Existing full-array config API remains.

Run `python3 scripts/test_engine.py SPARE_IP` for clock transitions, rule errors,
output failures/recovery, runtime manual control and real-SNTP-to-mock integration.
The script restores original relay configuration, timezone and clock-source mode.
No physical GPIO diagnostic was run during this software-only milestone.
