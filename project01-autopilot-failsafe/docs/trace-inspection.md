# Independent inspection of simulator traces

This inspection reads the onboard DataFlash binary logs with `pymavlink.DFReader.DFReader_binary`. The script imports neither the runner nor the scenario evaluator. It separately decodes `rx.tlog` to compare telemetry mode observations with onboard mode records. DataFlash and MAVLink provide separate logging paths from the same simulator; both decoders are supplied by the pinned pymavlink package. This check covers the recorded experiment. Independent physical-model validation remains outside its scope.

The script verifies its input hashes against each run's `SHA256SUMS` before reading records. The JSON report retains its own script hash and pymavlink version, input hashes, exact event markers, raw mode/error/arming records, selected messages, and timing comparisons. Non-finite raw floats, including absent PARM default values, are retained as explicit `NaN`, `Infinity`, or `-Infinity` strings in strict JSON. The operator annotations below are direct assistant inspection of those records on 2026-10-17 America/Toronto. No human review is claimed, and the user's specification does not require a separate qualified-human approval gate.

## Fields and interpretation

The log supplies its field layouts in FMT records. The pinned upstream [logger definitions](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_Logger/LogStructure.h) identify `MODE.TimeUS` as startup-relative time, `Mode` as the vehicle-specific mode, and `Rsn` as the mode-change reason. The field is named `Rsn` in these actual logs. `TimeUS / 1,000,000` gives simulator seconds. Copter modes 4 and 9 are GUIDED and LAND.

The pinned [ModeReason enum](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_Vehicle/ModeReason.h) assigns reasons 2 to a GCS command, 3 to radio failsafe, 4 to battery failsafe, 5 to GCS failsafe, and 6 to EKF failsafe. Repeated MODE records with the same mode are retained in the JSON, then collapsed only for comparison of state transitions.

The pinned [logger enums](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_Logger/AP_Logger.h) identify `ERR.Subsys` 5 as radio failsafe, 6 as battery failsafe, 8 as GCS failsafe, and 17 as EKF failsafe. For these subsystems, `ECode=1` records occurrence and `ECode=0` records resolution. Different subsystems can give the same error code different meanings. A cleared compass record at startup is not a link failsafe.

[Battery log definitions](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_BattMonitor/LogStructure.h) identify `BAT.Volt` as measured voltage and `Inst=0` as the first monitor. [GPS log definitions](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_GPS/LogStructure.h) identify `GPS.Status` as fix type and `GMS` as milliseconds within the GPS week. GMS is a sensor time field and cannot be substituted for the autopilot's `TimeUS`.

The independent comparison preserves both exact DataFlash timestamps and the MAVLink reader's most recently received SYSTEM_TIME value. That MAVLink assignment can precede the actual mode change by part of a sampling interval. The difference is reported directly; it is not interpreted as a negative physical reaction time.

## Baseline used to verify the reader

The development baseline `evidence/development/baseline-04` contains these direct DataFlash observations:

| Record | Simulator time, s | Meaning |
|---|---:|---|
| MODE 4, Rsn 2 | 42.234766 | GCS requested GUIDED |
| ARM, ArmState 1, ArmChecks 1, Forced 0 | 42.334726 | Normal checked arming |
| MODE 9, Rsn 2 | 68.856613 | GCS requested LAND |
| ARM, ArmState 0, Method 13 | 93.889096 | Logged disarming |

The independently decoded MAVLink LAND observation is assigned 68.834 s, 0.022613 s before the DataFlash transition. Both record the same state sequence. The DataFlash dropped-record counter remains zero in this baseline.

## GCS recovery on release 4.5.6

Direct inspection of `evidence/full/4.5.6/04-gcs-recovery/schedule-0.0` found:

| Record or event | Simulator time, s | Interpretation |
|---|---:|---|
| Heartbeat-stop event | 61.432000 | Runner's recorded injection marker |
| ERR Subsys 8, ECode 1; MSG `GCS Failsafe` | 64.441713 | Onboard detector observed GCS timeout |
| MODE 9, Rsn 5 | 64.441713 | GCS failsafe requested LAND, 3.009713 s after the marker |
| Heartbeat-restoration event | 69.432000 | Runner resumed heartbeat transmission |
| ERR Subsys 8, ECode 0; MSG `GCS Failsafe Cleared` | 69.762084 | Onboard detector cleared 0.330084 s after restoration |
| ARM, ArmState 0 | 93.479260 | Logged disarming |
| Observation endpoint | 118.334000 | No intervening MODE record leaves LAND |

The MAVLink reader assigns LAND to 64.434 s, 0.007713 s before its exact DataFlash time. Both logs agree on GUIDED followed by LAND. The complete DataFlash interval contains no dropped-record counter increase, and its absolute counter is zero. This supports the stated recovery behavior for this run: restored GCS contact cleared the detector while the vehicle retained LAND.

## GPS input starvation on release 4.5.6

Direct inspection of `evidence/full/4.5.6/09-gps-stale/schedule-0.0` found:

| Record or event | Simulator time, s | Interpretation |
|---|---:|---|
| GPS Status 6, GMS 252879400, NSats 10 | 61.424587 | Last valid GPS record before injection |
| `SIM_GPS_BYTELOSS=100` event | 61.432000 | Runner's recorded injection marker |
| GPS Status 0, GMS 0, GWk 0, NSats 0 | 65.404661 | GPS driver cleared the absent receiver, 3.972661 s after the marker |
| ERR Subsys 16, ECode 2 | 69.364743 | EKF checker reported bad state |
| ERR Subsys 17, ECode 1; MODE 9, Rsn 6 | 69.364743 | EKF failsafe requested LAND, 7.932743 s after the marker |
| ARM, ArmState 0 | 98.699671 | Logged disarming |

The onset includes the logged messages `EKF variance` and `EKF Failsafe: changed to LAND Mode`. The receiver timeout starts from its last received message, so its interval relative to the later injector marker can be slightly less than four seconds. The complete log has no reported dropped records. MAVLink assigns LAND to 69.332 s, 0.032743 s before the exact onboard record.

These records establish loss of fresh GPS input and an EKF-triggered transition in this configured simulation. They do not exercise a receiver that repeatedly emits frozen coordinates with fresh timestamps and valid status.

## Simultaneous GCS and RC loss on release 4.5.6

Direct inspection of `evidence/full/4.5.6/10-gcs-rc-compound/schedule-0.0` found:

| Record or event | Simulator time, s | Interpretation |
|---|---:|---|
| Heartbeat-stop and `SIM_RC_FAIL=1` events | 61.432000 | Equal sampled simulator times; host event markers are 0.147042 ms apart |
| ERR Subsys 2, ECode 2 | 62.444179 | RC late-frame condition |
| ERR Subsys 5, ECode 1; MSG `Radio Failsafe` | 62.444179 | Radio failsafe observed |
| MODE 9, Rsn 3 | 62.444179 | Radio failsafe requested LAND, 1.012179 s after its marker |
| ERR Subsys 8, ECode 1; MSG `GCS Failsafe` | 64.441713 | GCS failsafe independently observed |
| ARM, ArmState 0 | 91.486724 | Logged disarming |
| Observation endpoint | 118.334000 | LAND remained the last recorded mode |

Both detectors are visible in onboard records. Radio failsafe caused the first LAND transition; GCS failure arrived while LAND was already active. This checks both fault observations and the resulting state, without claiming that the trace shows two independently caused mode changes. MAVLink assigns LAND to 62.434 s, 0.010179 s before the exact onboard record.

One DataFlash record had been dropped by the first DSF statistics sample at 3.267026 s. The drop counter did not increase between the healthy-hover marker at 56.334 s and the observation endpoint. The missing startup record remains unidentified.

## Logging limitation

During development of the independent reader, the completed starter battery trace had `DSF.Dp=1` by its first statistics record at 3.267026 s. The counter did not increase during the declared observation window, which started at 56.334 s. Its battery failsafe ERR record and LAND transition were both present at 64.664124 s, alongside the low-battery MSG record. The reader therefore reports startup drops separately from new drops during observation. A zero-growth counter does not recover the missing startup record or identify its type.

The reader's completeness crosscheck requires no increase in the drop counter during the observation interval. All absolute counts remain in the report. This crosscheck supplements the original scenario evaluator and does not change its state-transition or deadline assertions.

## Reproduce this inspection

From the project directory, using Bash or Fish:

```sh
.venv/bin/python scripts/inspect_dataflash.py evidence/development/baseline-04 evidence/starter/4.5.6/02-battery-low/schedule-0.0 evidence/full/4.5.6/04-gcs-recovery/schedule-0.0 evidence/full/4.5.6/09-gps-stale/schedule-0.0 evidence/full/4.5.6/10-gcs-rc-compound/schedule-0.0 --output evidence/trace-inspection.json
```

The retained report contains five real traces: the development baseline, starter battery case, and the three required representative full-suite cases. Its 23 crosschecks pass. The required recovery, stale-input, and compound cases contribute 15 of those checks. Both records of one startup drop are reported, and all five observation intervals have zero additional drops. This establishes the requested independent trace inspection for release 4.5.6. Release 4.5.7 is covered separately by the suite evaluator and release comparison.
