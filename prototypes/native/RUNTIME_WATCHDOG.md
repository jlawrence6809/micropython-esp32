# Continuous runtime health — software-only spare milestone

Normal firmware now keeps the boot-health task running after OTA validation.
This is an **application progress monitor**, not an independent hardware watchdog
or a promise that Wi-Fi/HTTP will always be reachable. No controller build was
booted or armed for these tests; no live controller was accessed.

## Behavior

- Rules, network retry, USB and input sampler each increment an atomic heartbeat.
- Initial health is unchanged: selftests, minimum heap and progress from all four
  tasks, at least five seconds after startup. Missing Wi-Fi/NTP does not itself
  fail health. Pending images that cannot establish health are still rolled back.
- After validation, the monitor samples progress every second. Ten seconds without
  observed progress from any task clears health and restarts the **same image**.
  Counter and 32-bit millisecond rollover are covered by pure boot selftests.
- A valid image is not automatically rolled back after a runtime stall: settings
  could have changed since its predecessor. Recovery requires inspection and an
  explicit compatible OTA/USB action, not speculative downgrade/replay.
- A magic/inverse-checked RTC no-init record reports the previous software-watchdog
  mask once after restart. This is a best-effort volatile diagnostic, not durable
  reset history. No NVS/configuration/flash write occurs on timeout.
- Bit masks: rules=1, network=2, USB=4, inputs=8. `GET /api/watchdog/status` exposes
  monitor state, observed progress ages, timeout and previous masks, and diagnostic
  build flags. `/api/ota/status` also includes monitor state and previous mask.
- Reset restores configured boot defaults. This is **not** verified electrical
  shutdown: ROM/startup levels, contacts, brownouts and safe boot defaults still
  require attended hardware testing. A scheduling discontinuity still skips missed
  edge transitions rather than catching up.

The monitor allocates no periodic heap and takes no application mutex. The former
boot task retains its 4096-byte stack. If the scheduler/monitor itself cannot run,
this layer cannot enforce a deadline; platform watchdogs and hardware recovery are
separate layers. Heartbeats show progress, not semantic correctness or successful
radio/clock service. HTTP is not treated as a fifth heartbeat: normal idle periods
are valid and a deliberately slow upload is allowed its separate bounded window.

## Request-body bound

Generic JSON/rule HTTP requests now have a five-second overall body-receive budget,
checked after each socket read. A slowly trickling body can no longer extend the
per-read timeout indefinitely. Over-budget bodies get HTTP 408 and the connection
is closed **before dispatch**, including if the last chunk completes the body.
Oversized declarations are rejected and closed rather than allowing SDK cleanup
to purge the whole declared stream. A bounded 16-KiB/250-ms cooperative discard
window lets ordinary small oversized clients receive HTTP 413 before TCP close;
one blocking read can add its configured timeout. Very large/incomplete streams
can still end with a connection reset rather than a readable error response.
The blocking per-read timeout can extend wall time beyond five seconds; this is
not a hard real-time deadline. Headers are still parsed by the SDK, not by this
body guard. Dedicated OTA streaming retains its own timeout/integrity checks.

## Spare-only fault fixture

`CONFIG_BENCH_WATCHDOG_STALL` stops one selected task only **after** local health
validation. It will repeatedly reset that image until normal firmware is restored.
All three bench diagnostics (watchdog stall, pending-boot rollback, physical I/O)
are mutually exclusive and forbidden in controller firmware at compile time.

```sh
bash scripts/build.sh -B build-watchdog \
  -DSDKCONFIG="$PWD/build-watchdog/sdkconfig" \
  '-DSDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.watchdog-test.defaults'
python3 scripts/test_watchdog.py SPARE_IP build-watchdog/garden_native_probe.bin --task 0
```

Fresh defaults select rules/task 0. To test 1/2/3, explicitly change
`CONFIG_BENCH_WATCHDOG_STALL_TASK` in that build's sdkconfig and rebuild; existing
sdkconfig values override defaults. The test verifies the expected selected task,
new boot ID, unchanged slot/hash, correct previous mask and preserved profile.
Its `finally` inspects the running hash before restoring the verified normal image;
it never blindly repeats an uncertain upload. Use only the disconnected spare.

`test_build_guards.py` uses the normal build's compilation database for syntax-only
negative compiler tests; it performs no device I/O. `test_runtime_stress.py` runs
bounded two-client HTTP work and a slow-body rejection test, with no persistent
configuration writes or output changes. Both device tests refuse controller roles;
the stress/fault tests additionally require the GPIO adapter to be absent.

## Verified observations

- Actual post-validation stalls in **all four tasks** caused same-image restarts,
  with masks 1, 2, 4, 8 and preserved application profile. Normal memory-only
  firmware was restored after each case. The input-stall case was repeated and
  passed end-to-end after tooling improvements described below.
- One 45-second two-client run: **1,235 requests, zero transport/protocol failures**,
  maximum response 0.305 seconds. Valid rules, runaway/allocation failures,
  snapshots, invalid typed inputs and excessive JSON depth were exercised.
- A second 45-second run: 1,162 requests, zero failures, max 0.088 seconds. Final
  bounded-discard version: 375 requests/15 seconds, zero failures, max 0.070 seconds;
  sampled heap 189,504 -> 193,052. An oversized 100-MB declaration with only one
  body byte was rejected and closed without purging that whole stream. Ordinary
  13,000-byte oversized input still returns the expected HTTP 413.
- Trickle-body test returned 408 at approximately 6.6 seconds; subsequent requests
  worked on the same boot, with no watchdog reset or profile/output change.
- Sampled heap: 193,492 -> 193,308 bytes after that run. Separate USB regression:
  200 evaluations, 193,496 -> 193,496. These are short observations, not leak proof.
- Backend lifecycle/role guards, complete profiles/pending-write gates, USB
  persistence/defaults, shared engine, clock/DST and ordinary HTTP regressions pass.
- Twelve later idle-spaced GET probes succeeded, approximately 0.10–0.12 seconds
  each after the first. This is not an extended network soak.

**Unresolved:** several individual four-second HTTP reads timed out during this
milestone, including post-reset/OTA verification and later read-only inspection.
USB and subsequent HTTP inspection confirmed normal healthy firmware with GPIO
absent; uploads were not repeated. Radio snapshot: RSSI -53, no recorded Wi-Fi
disconnects in that boot. The cause is not established. Tooling now makes up to
three explicitly logged transport-only attempts for initial role/post-OTA GET
verification; it never retries HTTP rejections or mutations. Timed stress requests
remain single-attempt so failures are not hidden by that helper. Do not claim this
monitor resolves radio/TCP reachability. Correlated diagnostics and longer network,
idle/reconnect/load/power testing remain release work.

Garden's native adapter now includes atomic partial-update APIs and serialized
AUTO/config/rule autosave; client calls passed against the memory-only spare. See
ATOMIC_EDIT.md for conflict, boot/generation and output-preservation semantics. Phone rendering/publishing
and production commissioning tooling remain separate gates. Sync state was checked
through an existing authenticated source-host route; no SSH trust or sync-service
settings were changed. See FIRST_RELEASE.md and GPIO_BACKEND.md for remaining gates.
