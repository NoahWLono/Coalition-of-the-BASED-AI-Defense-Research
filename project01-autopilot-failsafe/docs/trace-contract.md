# Trace and assertion contract v1

**Public-copy note:** the original recording and permission-setting workflow below describes the private experiment. The published evidence subsequently received fictional host identifiers and local paths, recomputed telemetry checksums, and new publication seals. Private originals remain unchanged. See the [publication redaction record](publication-redaction.md) for the permitted field changes, before/after checks and original hash commitments.

Each case directory contains `scenario.json`, `events.jsonl`, `rx.tlog`, `tx.tlog`, `timing.jsonl`, `params-before.json`, `params-after.json`, `run.json`, `sitl.stdout`, and `logs/*.BIN`.

Tlogs use standard pymavlink timestamp-prefixed MAVLink packets (unsigned big-endian 64-bit microseconds since Unix epoch). The offline reader uses SYSTEM_TIME.time_boot_ms for simulator time, carrying the last value forward between messages. `timing.jsonl` records rx sequence, host monotonic nanoseconds, and current simulator seconds. These are different clocks and must not be mixed. All events include `id`, `kind`, `sim_s`, `host_monotonic_ns`, `host_unix_us` and action details. The `baseline_ready` event records a completed stable hover. `scenario_end` marks the last observation, before teardown.

A JSON scenario contains `schema_version`, `id`, `title`, `starter`, `parameters` overrides, `preconditions`, `events`, `assertions`, `duration_s`, `cleanup`, and `rationale`. Events contain `id`, `at_s` relative to baseline_ready, `kind` (heartbeat, parameter, mode), and the required values (`enabled`; `name` and `value`; or `mode`). Assertions refer to an event by `after`, with `within_s` and optional `start_s` or `duration_s`. Types:

- `mode`: any allowed numeric custom_mode appears in an autopilot HEARTBEAT after the event within the deadline.
- `hold_mode`: all observed heartbeat modes in [event+start_s, event+start_s+duration_s] belong to `allowed`; require coverage and multiple observations.
- `text`: STATUSTEXT contains `contains`, or at least one nonempty string from `contains_any`, case-insensitively within the deadline. Supplying both forms, an empty list, or a malformed alternative is INDETERMINATE. Corpus 1.0.1 uses alternatives only for the documented GCS/battery ordering branch.
- `field`: a named MAVLink `message` has a `field` satisfying `op` (`lt`, `le`, `eq`, `ge`, `gt`) against `value` within deadline.
- `disarmed`: an autopilot heartbeat has armed flag clear within deadline.
- `heartbeat_gap`: TX has no GCS heartbeat for `duration_s` after the event, with logged heartbeat before the event and adequate RX time coverage after it. Recovery may then resume heartbeats.
- `heartbeat_resumed`: a TX GCS heartbeat after the recovery event within deadline.

Assertions marked `fault_evidence: true` must all pass before a case can PASS. Parameter echo alone is not physical fault evidence. Require status texts, raw battery/RC/GPS readings or TX silence as appropriate. Always require a completed baseline, an observed end beyond each assertion's window, sufficient clock coverage and a clean runner exit. Outcomes are PASS, FAIL (observed mismatch), INDETERMINATE (missing/unusable evidence). Negative controls keep the original assertion so the mismatch is observable.

`run.json` stores version, binary hash, command, return status, error if any, host and namespace details, wall duration, schedule offset, and cleanup. The evaluator must not trust a runner-supplied success verdict as a flight assertion. A `SHA256SUMS` file seals raw evidence before evaluation. Results are separate from the seal.

## Recorded evidence-quality limits

The requested SYSTEM_TIME period is 0.1 simulator second and HEARTBEAT period is 0.2 second. Untimestamped telemetry uses the last received clock sample. Onboard DataFlash timestamps cross-check selected transitions. Latency values therefore represent sampled observations, not exact physical response times.

The final evaluator requires a stable three-second baseline with at most 0.5 s between samples or at interval endpoints: GUIDED and armed, altitude 10.5 to 13.5 m, absolute vertical speed at most 30 cm/s, valid GPS fix, and battery voltage above 11,500 mV. Armed GUIDED state must also persist with heartbeat coverage until the first fault event. Scheduled events must occur no more than 0.5 simulator second late and no more than 0.002 s early. Events declared at the same time must be within 0.25 s of one another. Parameter faults require both transmitted PARAM_SET and the subsequent matching PARAM_VALUE within five seconds.

Assertions require simulator-clock coverage, with no gap or endpoint distance greater than 2.5 s. Sustained modes also require heartbeat coverage. A witnessed threshold match satisfies an existential field assertion; a negative threshold determination requires usable sensor-stream coverage. Missing coverage yields INDETERMINATE. Observations after scenario_end cannot satisfy assertions, and invalid battery/GPS sentinel values do not count as measurements. These are sampled-data assertions and cannot exclude an unobserved transient between samples.

A disabled-GCS negative control counts only when prerequisite checks and heartbeat silence pass, the expected LAND and disarm assertions fail, and the observed vehicle remains armed in GUIDED. A wrong-mode replay counts only when the targeted mode assertion fails and the other assertions pass. A headline FAIL alone never qualifies a control.

At teardown, the runner closes writers, computes the evidence seal, and marks raw files read-only. Derived result.json files stay writable for evaluator replay. The seal is an integrity check within the local review workflow, not a signed external attestation. Existing completed runs from before the permission-setting addition are frozen the same way before final evaluation; their bytes and original seals stay unchanged.
