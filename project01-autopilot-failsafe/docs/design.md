# Experiment design, recorded before runner implementation

This laboratory tests ArduCopter 4.5.6 and 4.5.7 using the official Linux x86_64 SITL binaries and their built-in quad model. It does not assess aircraft flight safety. The supplied project specification is the approved scope. The implementation choices below are assistant-selected.

The civilian task is a stationary hover at 12 m above a fictional flat site at latitude 0.01 degrees, longitude 0.01 degrees, elevation 0 m. No map service is used. A baseline must boot, obtain a GPS/EKF position, arm, climb, and hold GUIDED before any fault is scheduled. Normal arming checks remain enabled. Each scenario starts with erased persistent state and its own output directory.

## Initial transition table

These expectations precede implementation. LAND means mode 9 observed in autopilot telemetry; it does not prove a safe touchdown. The first three cases also require eventual disarming within the observation window.

| Starter case | Preconditions | Fault | Expected transition | Deadline in simulator seconds | Basis |
| --- | --- | --- | --- | --- | --- |
| 01 GCS loss | GUIDED, armed, altitude at least 10 m, GPS fix, GCS heartbeats established; FS_GCS_ENABLE=5, FS_GCS_TIMEOUT=3, FS_OPTIONS=0 | Stop GCS heartbeats after 5 s baseline | GUIDED to LAND; GCS failsafe text must occur | 8 s from heartbeat stop | 3 s configured timeout plus scheduler and telemetry margin |
| 02 low battery | Same hover; battery initially above 11 V; BATT_FS_LOW_ACT=1, BATT_LOW_VOLT=11, BATT_LOW_TIMER=3, BATT_LOW_MAH=0 | SIM_BATT_VOLTAGE=10.5 | Voltage below threshold, battery failsafe text, GUIDED to LAND | 12 s | 3 s timer plus voltage filter and observation margin |
| 03 RC loss | Same hover; FS_THR_ENABLE=3, RC_FS_TIMEOUT=1, FS_OPTIONS=0 | SIM_RC_FAIL=1 (no pulses) | Radio failsafe text, GUIDED to LAND | 6 s | 1 s timeout plus scheduler and telemetry margin |

The official GCS and radio documentation says restored links do not automatically restore the previous flight mode. Recovery cases must therefore remain in the failsafe mode until an explicit mode request. Source review will define stale GPS, threshold-boundary and compound extensions before their runs. Unknown outcomes stay indeterminate or failed; expectations will not be weakened to match a trace.

## Isolation and evidence

Run serially inside Bubblewrap user, PID, IPC, UTS and network namespaces, with a private /dev, private /tmp, read-only host filesystem, and only this project writable. Networking has only loopback and no route to the host LAN or Internet. The pinned SITL source hardcodes a wildcard RC UDP socket. Its namespace contains only loopback, so it is confined locally; the report must show the actual socket rather than claim a literal loopback bind. Use a loopback TCP listener in the harness and SITL TCP client, with unused serial channels disabled. No MAVProxy discovery, hardware UART, radio, external simulator, or hardware bridge is enabled. If isolation fails, stop simulator execution.

Record received and transmitted MAVLink bytes in separate timestamped binary logs. The runner records monotonic host times and simulator SYSTEM_TIME independently. Raw autopilot DataFlash logs provide a second reader path. The evaluator reads saved MAVLink logs and declarative assertions, does not call the runner, and verifies fault evidence before state assertions. Seal complete evidence with SHA-256 hashes and reject changed evidence. Missing observations are not passes.

## Bounds and repeatability

One SITL process at a time, speedup 4, fixed simulator start time (Unix 1700000000), no GPU, two CPU affinity slots, 1.5 GiB address-space limit per child, 180 s wall timeout per scenario, and at most 150 MiB initial downloads. Repeats vary event schedules by 0, 0.7 and 1.4 simulator seconds. No claim is made that a random seed controls internal SITL noise. Logs retain both simulator duration and wall duration.

The twelve cases, two baselines, starter runs, timing repeats, disabled-failsafe negative control and wrong-expectation replay form the completed suite. A source review, independent DataFlash inspection of recovery and compound cases, and a final code review constrain conclusions.

Primary references checked on 2026-10-17 America/Toronto: [SITL](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html), [using SITL](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html), [GCS failsafe](https://ardupilot.org/copter/docs/gcs-failsafe.html), [radio failsafe](https://ardupilot.org/copter/docs/radio-failsafe.html), and [battery failsafe](https://ardupilot.org/copter/docs/failsafe-battery.html). Current documentation may describe newer releases, so pinned source and parameter readback govern this experiment.
