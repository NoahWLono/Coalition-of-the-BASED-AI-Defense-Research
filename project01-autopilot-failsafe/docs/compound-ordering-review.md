# GCS and battery failsafe ordering review

The failed assertion in `evidence/full/4.5.7/11-gcs-battery-compound/schedule-0.7` rejects an expected source branch. Battery failsafe selected LAND before GCS failsafe occurred. The GCS handler then reported `GCS + Battery Failsafe - Continuing Landing`, as both pinned releases explicitly implement. This message does not contain the assertion's required substring `GCS Failsafe`. These four traces establish a difference in detector ordering; they provide no evidence of a regression in the required LAND response.

This is direct assistant inspection, completed at 2026-10-18 02:26:55 UTC (2026-10-17 22:26:55 America/Toronto). No qualified human review is claimed. The original failed result, scenario, raw logs, and evaluator remain unchanged by this review. The supplemental [machine-readable inspection](../evidence/compound-ordering-inspection.json) retains decoded onboard records, independent MAVLink observations, hashes, and the original evaluation outcomes.

The pinned [`failsafe_gcs_on_event` implementation](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/ArduCopter/events.cpp#L208-L211) checks whether the vehicle is already landing and battery failsafe requires landing. It then announces the combined message and retains LAND. This branch is independent of the `FS_OPTIONS` continue-landing option. The same complete `events.cpp` file is present in [4.5.6](https://github.com/ArduPilot/ardupilot/blob/7ce11b4194f6c6b77d8e1f2bd5f14c0466d5e696/ArduCopter/events.cpp#L208-L211) and 4.5.7: both locally preserved copies have SHA-256 `62992c7e68cf184a7e07b9204497613cb41a3a8ed51ec4aab966ee04d5737cfe`. This hash matches the source manifest. Their battery-monitor source files also match their saved hashes.

The GCS timeout measures elapsed time since the last received heartbeat. The battery timeout measures elapsed time since its monitor first detects low voltage. Equal injector timestamps do not require the detectors to fire in a fixed order. The observed ordering difference is consistent with those separate clocks. These traces do not isolate which heartbeat or scheduler phase produced it.

`DFReader_binary` decoded all four onboard logs independently of the runner and oracle. Times below are exact DataFlash `TimeUS / 1,000,000`, except the fault marker, which is the runner's sampled simulator clock. `ERR.Subsys=8` identifies GCS failsafe and `ERR.Subsys=6` battery failsafe; both use `ECode=1` for occurrence. LAND is mode 9. Reason 5 identifies GCS failsafe; reason 4 identifies battery failsafe.

| Release / schedule | Fault marker, s | GCS ERR, s | Battery ERR, s | First LAND, s / reason | Disarm, s | Original oracle |
|---|---:|---:|---:|---|---:|---|
| 4.5.6 / 0.0 | 61.432 | 64.441713 | 64.664124 | 64.441713 / 5 | 93.621703 | PASS |
| 4.5.6 / 0.7 | 62.134 | 65.107280 | 65.264717 | 65.107280 / 5 | 94.274775 | PASS |
| 4.5.7 / 0.0 | 61.432 | 64.441713 | 64.564164 | 64.441713 / 5 | 93.616705 | PASS |
| 4.5.7 / 0.7 | 62.134 | 65.439647 | 65.264717 | 65.264717 / 4 | 94.437210 | FAIL: assertion-02 only |

In the failed run, battery failsafe precedes GCS failsafe by 0.174930 s. At 65.264717 s the log contains `ERR(6,1)`, `MODE(9,Rsn=4)`, the measured low-voltage message, and `Battery Failsafe`. At 65.439647 s it contains `ERR(8,1)` and the combined message. LAND remains the recorded mode through the observation endpoint at 119.132 s. Battery voltage ranges from 12.600000 V to 10.500000 V in the inspected interval. The other three traces contain the plain `GCS Failsafe` message because their GCS detectors fire first.

The independently decoded MAVLink log assigns the failed run's LAND and battery messages to 65.232 s, and the combined message to 65.432 s. Those assignments precede the onboard times by 32.717 ms and 7.647 ms respectively because the decoder carries the most recently received SYSTEM_TIME value. They agree on ordering and mode. All four logs have an absolute DataFlash dropped-record count of zero, cover their observation endpoints, and agree with MAVLink on the mode sequence.

The supplemental report records 32 passing checks: 16 existing reader checks across four runs, plus four source-consistency checks per run. The latter confirm both detector occurrences within their declared windows, the LAND reason matching the first detector, the GCS message matching the source branch at the detector timestamp, and LAND persistence with disarming within 50 s. These supplemental checks do not change the original result: its eleven run checks and seven other assertions passed, while assertion-02 failed.

The concrete oracle correction is to accept either explicit GCS occurrence message for this compound case: `GCS Failsafe` or `GCS + Battery Failsafe - Continuing Landing`. Preserve the heartbeat-loss proof, low-voltage proof, LAND deadlines, hold interval, and disarm deadline. A generic `Failsafe` substring would be too broad because it could match battery failsafe without proving GCS detection. Version any corrected corpus and retain the original failed evaluation as evidence of the oracle defect.

The raw independent read can be reproduced from the project directory without running the simulator:

```sh
.venv/bin/python scripts/inspect_dataflash.py evidence/full/4.5.6/11-gcs-battery-compound/schedule-0.0 evidence/full/4.5.6/11-gcs-battery-compound/schedule-0.7 evidence/full/4.5.7/11-gcs-battery-compound/schedule-0.0 evidence/full/4.5.7/11-gcs-battery-compound/schedule-0.7 --output /tmp/compound-independent-read.json
```

The retained report adds this review's source hashes, original result hashes, and source-consistency annotations to that decoder output. It supplements the required three-trace inspection in [trace-inspection.md](trace-inspection.md). It does not independently validate the simulator's physical model.
