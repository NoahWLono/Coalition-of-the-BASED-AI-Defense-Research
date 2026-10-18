# Release comparison

The complete local experiment executed twelve fault scenarios on ArduCopter 4.5.6 and 4.5.7, including schedule repeats, recovery paths and simultaneous faults. Both releases reached the declared states within the tested deadlines. One repeated compound case exposed an overly narrow status-text expectation in corpus 1.0.0. Its original FAIL remains recorded. A source-backed correction in corpus 1.0.1 passes a separate retrospective evaluation of the same sealed evidence. This experiment found no state-transition regression between the two pins within this configuration.

The experiment establishes simulator behavior under the listed assertions. It does not establish operational flight safety. All labels, source reviews and trace annotations were produced by assistants; no qualified human certification is claimed.

## Executed results and the corpus correction

The starter stage first completed a healthy baseline and three fault cases on 4.5.6: GCS heartbeat loss, low battery and simulated RC pulse loss. The full stage then completed 58 fresh simulator runs in 1,902.1 wall seconds, about 31.7 minutes. There were two baselines, 54 enabled-failsafe fault runs and two disabled-GCS controls. Every fault case ran at offsets 0 and 0.7 simulator seconds on both releases. GCS loss, battery low and GPS starvation also ran at offset 1.4 seconds.

The final evaluator replayed all 58 sealed traces using their original executed expectations. Its [machine-readable comparison](../evidence/full/comparison.json) reports 55 PASS and three FAIL, with no INDETERMINATE. Two failures are the deliberately disabled-GCS controls, each qualified by confirmed heartbeat silence, continued armed GUIDED state, and missing LAND/disarm responses. The third is the compound text mismatch described below. The original `gates_resolved` remains false.

| Scenario | Runs per release | Original 4.5.6 | Original 4.5.7 | Observed LAND latency range, simulator s |
| --- | ---: | --- | --- | ---: |
| Persistent GCS heartbeat loss | 3 | 3 PASS | 3 PASS | 2.900 to 3.298 |
| Low battery voltage | 3 | 3 PASS | 3 PASS | 3.098 to 3.202 |
| RC pulse loss | 2 | 2 PASS | 2 PASS | 0.998 to 1.002 |
| GCS recovery after failsafe | 2 | 2 PASS | 2 PASS | 3.002 to 3.298 |
| RC recovery after failsafe | 2 | 2 PASS | 2 PASS | 0.998 to 1.002 |
| Battery recovery after failsafe | 2 | 2 PASS | 2 PASS | 3.098 to 3.202 |
| Brief GCS interruption | 2 | 2 PASS | 2 PASS | Remained GUIDED until commanded landing |
| Brief battery dip | 2 | 2 PASS | 2 PASS | Remained GUIDED until commanded landing |
| GPS byte starvation | 3 | 3 PASS | 3 PASS | 7.798 to 7.902 |
| GCS and RC loss | 2 | 2 PASS | 2 PASS | 0.998 to 1.002 |
| GCS loss and low battery | 2 | 2 PASS | 1 PASS, 1 text FAIL | 2.898 to 3.098 |
| GPS starvation and RC loss | 2 | 2 PASS | 2 PASS | 0.902 to 1.002 |

Ranges combine both releases and schedules. Compound ranges describe the resulting LAND state. Both detectors or input failures are checked independently; a shared LAND observation cannot establish two separate causes. In recovery cases, the observed mode stayed LAND after the input was restored.

In `4.5.7/11-gcs-battery-compound/schedule-0.7`, the onboard log records battery failsafe and LAND at 65.264717 s, followed by GCS failsafe at 65.439647 s. The resulting text is `GCS + Battery Failsafe - Continuing Landing`. The original assertion searched for the contiguous substring `GCS Failsafe`, which does not occur in that message. The other three executions of this compound case recorded GCS detection first and emitted the expected plain text. All four reached LAND and disarmed within their deadlines.

The [compound ordering review](compound-ordering-review.md) ties this alternate message to the explicit battery-first branch in pinned `events.cpp` lines 208–211. That source file is byte-identical across the releases. The evidence supports a detector-ordering difference across these particular executions; it does not establish a release-dependent regression, a probability of either ordering, or an identified cause for the scheduling difference.

Corpus [1.0.1](../scenarios/manifest.json) changes only that text assertion to permit either explicit GCS message. Events, parameters, state assertions and deadlines are unchanged. The full [1.0.0 corpus](../scenarios/history/1.0.0/manifest.json) and sealed per-run scenarios remain available. The [separate revision review](../evidence/full/corpus-revision-review.json) replays all four affected traces and reports four PASS. Combined with the unchanged cases and qualified controls, `revised_corpus_gates_resolved` is true. This is a retrospective assertion correction; the full simulator suite was not executed again after that correction. Future reproduction uses 1.0.1.

## Configuration and measurement

The pins are 4.5.6 commit `7ce11b4194f6c6b77d8e1f2bd5f14c0466d5e696` and 4.5.7 commit `2a3dc4b7bf2507120f7378a7b2fde73185e0c325`. The [manifest](../manifest.json) records binary hashes, 2024 source dates, exact dependencies and official download locations. These historical releases were selected for compatible official SITL binaries. They are not claimed to be current releases.

Both use the built-in quad/PLUS model, fictional location, 12 m healthy hover, synthetic start time, speedup 4, and the same input parameter files. Every one of the twelve primary comparison pairs has 1,385 initial parameter values on each release, with zero differing values. All cases passed the explicit parameter readback check. Relevant failsafe values are set rather than inherited: GCS action 5 with a 3 s timeout, radio action 3 with a 1 s timeout, battery LAND with an 11 V low threshold and 3 s timer, options 0, EKF action 1 and dead reckoning disabled. Receiver 2 is disabled for GPS starvation. The [source review](source-review.md) explains these choices and differences from current documentation.

The evaluator uses the last received SYSTEM_TIME for telemetry without its own timestamp. Clock sampling is 0.1 s and heartbeat sampling 0.2 s. A last-clock assignment can slightly precede the exact onboard transition. GCS deadlines also depend on the phase of the last transmitted heartbeat. The observed latency ranges therefore do not support fine-grained performance ranking between releases. Measured simulator speedup over the observation windows ranged from 3.9433 to 4.0044. Wall-time variation is separate from simulator-time assertions; its cause was not isolated.

The GPS LAND deadline of 40 s is an experimental bound for this EKF configuration, not a documented universal guarantee. All six GPS-only cases met it in about 7.8 to 7.9 sampled simulator seconds. A no-fault hover, confirmed fault input and continuous observation are prerequisites for a PASS. Missing coverage produces INDETERMINATE. This remains a sampled-data test and cannot exclude an unobserved transient between packets.

## Independent evidence and negative controls

The independent reader uses DataFlash onboard records and a separate MAVLink decode without importing runner or evaluator logic. Both decoders come from pymavlink, and both evidence paths originate in the same simulator. The [trace inspection](trace-inspection.md) documents field definitions and direct assistant inspection of five traces, with 23 passing crosschecks. Its three required representative full-suite traces cover GCS recovery, stale GPS and combined GCS/RC loss. Four additional compound GCS/battery traces were inspected when the unexpected text appeared; all 32 supplemental checks pass in the [ordering evidence](../evidence/compound-ordering-inspection.json).

Representative onboard records are:

| Trace | Independent record | Interpretation |
| --- | --- | --- |
| GCS recovery, 4.5.6 offset 0 | LAND reason 5 at 64.441713 s; GCS cleared at 69.762084 s; disarmed at 93.479260 s | Recovery cleared detection while LAND persisted |
| GPS starvation, 4.5.6 offset 0 | GPS status 0 at 65.404661 s; EKF failsafe and LAND reason 6 at 69.364743 s | Receiver timeout preceded EKF action |
| GCS/RC loss, 4.5.6 offset 0 | Radio failsafe and LAND reason 3 at 62.444179 s; GCS failsafe at 64.441713 s | RC initiated LAND; both detectors were recorded |
| GCS/battery, 4.5.7 offset 0.7 | Battery failsafe and LAND reason 4 at 65.264717 s; GCS failsafe at 65.439647 s | Battery-first branch explains the text mismatch |

Two of the first five inspected logs had one unidentified dropped DataFlash record before their first statistics sample at about 3.27 s. Neither counter increased during its fault-observation interval. Those startup records remain missing; a no-growth counter does not recover them. The four additional compound logs reported no drops.

Both disabled-GCS controls produced the intended mismatch. Two further offline replays, one per release, changed the expected mode from LAND to RTL while keeping the real packets unchanged; both failed only the intended mode assertion and passed the other assertions. The [short demonstration](../evidence/demo.txt) shows a real passing GCS-loss trace followed by that detected wrong expectation. It is a planted evaluator mismatch; no autopilot release regression was found.

All 41 unit tests pass, including missing data, tampered evidence, premature LAND, fault confirmation, malformed assertions and targeted control qualification. Synthetic fixtures are marked synthetic and do not count toward the real simulator results. Fresh-environment bootstrap, checksum rejection and artifact generation after a failing suite were also checked. The [review record](review-record.md) describes the defects found and corrected during implementation.

## Isolation, resources and cleanup

The [final audit](../evidence/full/provenance-isolation-audit.json) passed 522 provenance and isolation checks across 58 runs. It confirmed binary and live commit identities, configuration hashes, parameter readback, private loopback-only network namespaces, absence of hardware file descriptors and UART bridges, monotonic timing, and completed cleanup. No project simulator process remained. Every case closed its listeners before exit. Host network rules were not changed by this workflow.

The controller bound `127.0.0.1:5760`. The pinned SITL RC implementation bound `0.0.0.0:5501` inside a private namespace containing only loopback and no external route. This is locally confined, although the RC socket does not literally bind the loopback address. Private devices and disabled hardware bridges kept physical aircraft and radios outside the experiment.

The largest measured simulator child maximum RSS was 31.3 MiB. A sampled live parent high-water mark was 63.8 MiB; this was not a measurement of peak whole-machine memory. Each child was limited to a 1.5 GiB address space and two CPU affinity slots, with only one simulator active. The full suite retains about 589 MiB of evidence; starter and development evidence bring the total to about 647 MiB. Allow 1 GB per fresh reproduction plus dependencies and local version-control storage. The sum of case wall times was 1,783.2 s; orchestration and immediate evaluation brought the full stage to 1,902.1 s. Later review time is additional.

## Limits and next step

The required twelve cases, two-release execution, independent trace inspection and negative controls are complete. The original corpus retains one explained assertion mismatch. The revised corpus has passed retrospective evaluation; a fresh full execution of version 1.0.1 is not claimed.

Coverage excludes complete telemetry-transport failure, frozen valid GPS coordinates with fresh timestamps, conflicting failsafe action priorities, mission-continuation exceptions, SmartRTL, fences, receiver failover, other vehicle types and all physical flight behavior. Schedule offsets vary timing but do not control every internal random source. No failure probability or safety certification follows from these observations.

The next concrete step is for a separate operator to run `bash scripts/reproduce.sh` from a clean supported Linux environment using corpus 1.0.1, retain the new output directory, and compare the compound detector ordering and state results with this report. No further optional simulator runs were added once the defined checks and the observed mismatch were resolved.
