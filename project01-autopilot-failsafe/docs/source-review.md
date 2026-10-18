# Primary-source review and scenario rationale

Reviewed on 2026-10-17 in America/Toronto; source inspection completed through 21:43:59 EDT (2026-10-18T01:43:59Z). These are documentation and source observations, not simulator results. Scenario outcomes belong in the executed evidence and comparison report. The descriptions below were produced by an assistant and have not received qualified human review.

ArduCopter has a native Linux SITL executable with its own quadcopter physics model. That permits a small headless laboratory without a separate graphics or dynamics service. The current official [SITL overview](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html) and [using SITL guide](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html) document direct simulation, parameter files, state persistence, MAVLink connections, and DataFlash logging. A fresh working directory or erased EEPROM is necessary for each experiment because changed parameters persist in `eeprom.bin`.

## Release pins

| Release | Official manifest commit | Source date | Linux binary listing |
|---|---|---|---|
| ArduCopter 4.5.7 | `2a3dc4b7bf2507120f7378a7b2fde73185e0c325` | 2024-10-07 16:30:57 +0900 | [6,802,848-byte executable, listed 2024-10-16](https://firmware.ardupilot.org/Copter/stable-4.5.7/SITL_x86_64_linux_gnu/) |
| ArduCopter 4.5.6 | `7ce11b4194f6c6b77d8e1f2bd5f14c0466d5e696` | 2024-09-03 08:12:32 +0900 | [6,802,848-byte executable, listed 2024-09-04](https://firmware.ardupilot.org/Copter/stable-4.5.6/SITL_x86_64_linux_gnu/) |

Both version manifests identify official firmware. The [4.5.7 git manifest](https://firmware.ardupilot.org/Copter/stable-4.5.7/SITL_x86_64_linux_gnu/git-version.txt) has a commit subject mentioning Plane but identifies `APMVERSION: ArduCopter V4.5.7`; retain that upstream metadata exactly. The [4.5.6 git manifest](https://firmware.ardupilot.org/Copter/stable-4.5.6/SITL_x86_64_linux_gnu/git-version.txt) identifies ArduCopter V4.5.6. These older releases were selected for compatible pinned semantics and available binaries. This review does not identify either as the newest release.

Fourteen relevant source files were retrieved at each exact commit. All fourteen pairs are byte-identical, including the failsafe action handlers, radio timeout logic, EKF check, battery checker, GPS simulator, parameter declarations, UART driver, and SITL input binding. `source-evidence/manifest.json` records each URL, length, and SHA-256. These snapshots total 678,004 bytes, plus the upstream GPL license. Equality of these selected files supports equivalent configuration; it does not establish equality of either complete executable or every runtime dependency.

## Intended transitions before execution

The first three cases establish the runner. All require a completed healthy takeoff and stable GUIDED hover, valid position, normal battery voltage, and enabled relevant failsafes. An armed vehicle that is still landed may disarm directly, so that condition cannot substitute for a hover precondition.

| Starter | Configuration | Supported fault | Expected transition | Suggested bound |
|---|---|---|---|---|
| GCS heartbeat interruption | `FS_GCS_ENABLE=5`, `FS_GCS_TIMEOUT=3`, `FS_OPTIONS=0`; heartbeat sender matches `SYSID_MYGCS` | Stop sender heartbeats after they have been observed | GUIDED → LAND → landed/disarmed | LAND within 8 simulator seconds of stopping; final disarm within 60 seconds from a 12 m hover |
| Battery low voltage | Working simulated battery monitor, `BATT_FS_LOW_ACT=1`, `BATT_LOW_VOLT=11`, `BATT_LOW_TIMER=3`, `BATT_FS_VOLTSRC=0`, `BATT_LOW_MAH=0`, `BATT_CRT_MAH=0`, `BATT_CRT_VOLT=0` | Set `SIM_BATT_VOLTAGE=10.5` | GUIDED → LAND → landed/disarmed | LAND within 12 simulator seconds; check measured voltage in addition to parameter acknowledgement |
| RC pulse interruption | `FS_THR_ENABLE=3`, `RC_FS_TIMEOUT=1`, `FS_OPTIONS=0`; no active RC override masks input | Set `SIM_RC_FAIL=1` | GUIDED → LAND → landed/disarmed | LAND within 6 simulator seconds; final disarm within 60 seconds |

These are laboratory acceptance bounds, with allowance for sampling and scheduling, not manufacturer response guarantees. The final corpus must specify its chosen altitude, descent settings, observation rate, and actual bounds. Exact transition time is bounded by the surrounding telemetry samples. A failsafe LAND request may include a four-second descent pause in these releases.

The following twelve-case design covers fault persistence, restoration, short disturbances, stale input, and simultaneous faults. It is a suggested design; the declarative corpus is the authority for what the runner executes.

| Case | Fault schedule relative to healthy-hover marker | Intended result and independent observation |
|---|---|---|
| 1. GCS loss | Stop heartbeats at time 0 and keep stopped | LAND within 8 s; GCS failsafe evidence and heartbeat absence |
| 2. Battery low | Reduce voltage at time 0 and keep low | LAND within 12 s; measured voltage below threshold for the configured timer |
| 3. RC loss | Stop pulses at time 0 and keep stopped | LAND within 6 s; radio failsafe evidence |
| 4. GCS restoration | Stop at 0; resume at 9 s, after LAND | Failsafe clears; LAND persists for the remaining descent |
| 5. RC restoration | Stop at 0; restore at 7 s, after LAND | Radio failsafe clears; LAND persists |
| 6. Battery restoration | Low at 0; restore nominal voltage at 13 s | Measured voltage recovers; LAND persists because battery failsafe is latched |
| 7. Brief GCS interruption | Stop at 0; restore at 1 s | GUIDED remains through a 10 s observation window; interruption and restoration both recorded |
| 8. Brief battery dip | Low at 0; restore at 1 s, below the 3 s timer | GUIDED remains through a 10 s observation window; measured dip and recovery required |
| 9. GPS stale input | `SIM_GPS_BYTELOSS=100` at 0; `GPS_TYPE2=0`, `FS_DR_ENABLE=0`, `FS_EKF_ACTION=1`, `FS_EKF_THRESH=0.8` | Fresh GPS measurements stop; GPS health degrades; position-dependent mode requests LAND within the provisional 40 s bound |
| 10. GCS and RC loss | Stop heartbeat and pulses at 0 | LAND within 8 s; both fault observations required even when RC acts first |
| 11. GCS and low battery | Stop heartbeat and reduce voltage at 0 | LAND within 12 s; both fault observations required |
| 12. GPS stale input and RC loss | Drop GPS bytes and stop RC pulses at 0 | LAND within 6 s through RC; GPS starvation must also become independently visible |

A provisional 40 s bound for the GPS-only LAND case allows the GPS driver timeout, estimator propagation, and a subsequent EKF check. The relevant documentation does not promise a universal GPS-loss-to-LAND deadline. The run must establish that the particular explicit configuration satisfies the bound or report a mismatch. Do not silently accept unrelated mode changes or adjust the bound after looking at a failing trace without versioning the expectation.

## Documented behavior and pinned implementation

The [GCS failsafe documentation](https://ardupilot.org/copter/docs/gcs-failsafe.html) defines a timeout after a previously connected GCS stops sending heartbeats. Action 5 requests LAND. Restoring contact clears the failure without restoring the former mode. A GCS that was never seen does not exercise this path. The pinned source checks the configured GCS system ID, clears RC overrides when GCS failsafe begins, and logs both occurrence and recovery. See [events.cpp](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/ArduCopter/events.cpp).

The [radio failsafe documentation](https://ardupilot.org/copter/docs/radio-failsafe.html) distinguishes missing RC pulses from low-throttle signaling. Restored radio input does not restore the former mode. In the pinned [radio.cpp](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/ArduCopter/radio.cpp), missing input is checked against `RC_FS_TIMEOUT`; the separate low-throttle path uses three consecutive low readings. Therefore a test of `SIM_RC_FAIL=2` is not a test of the no-pulse timeout used by value 1.

The [battery failsafe documentation](https://ardupilot.org/copter/docs/failsafe-battery.html) specifies low and critical thresholds, configurable voltage dwell time, and a latch that survives voltage recovery until reboot. The pinned [battery backend](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp) starts each timer when its voltage condition first holds, resets that timer when voltage recovers, and triggers when elapsed time is strictly greater than the positive timeout. Use measured voltage for proof of threshold crossing. Zeroing remaining-capacity thresholds avoids an unrelated trigger.

The current [EKF failsafe documentation](https://ardupilot.org/copter/docs/common-ekf-inav-failsafe.html) describes loss of estimator confidence and LAND in position-dependent modes. The pinned [ekf_check.cpp](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/ArduCopter/ekf_check.cpp) also treats loss of both relative and absolute position as failure. It checks at 10 Hz and requires ten failed checks after the estimator has previously passed. `FS_EKF_ACTION=1` requests LAND for a GPS-dependent mode. An active LAND switches to landing without GPS when necessary. The [dead-reckoning documentation](https://ardupilot.org/copter/docs/deadreckoning-failsafe.html) describes another response to position loss. Pin `FS_DR_ENABLE` explicitly so this separate behavior cannot accidentally decide the GPS case.

Pinned [parameter declarations](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/ArduCopter/Parameters.cpp) show that the GCS failsafe defaults disabled, `FS_OPTIONS` defaults to 16, and dead reckoning defaults to RTL. Explicit configuration is required. The selected LAND action values are `FS_GCS_ENABLE=5`, `FS_THR_ENABLE=3`, and `BATT_FS_LOW_ACT=1`; they are not interchangeable enums. The current EKF documentation mentions action 0 for reporting only, but these pinned parameter declarations expose actions 1, 2, and 3. The pinned handler's default branch requests LAND. Do not use action 0 as a negative control on these releases; use the documented disabling threshold instead.

## What stale GPS means here

The pinned [GPS simulator](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/SITL/SIM_GPS.cpp) makes three materially different experiments possible:

- `SIM_GPS_DISABLE=1` causes the first GPS to continue sending messages with no fix. That is sensor-health loss, not stale message delivery.
- `SIM_GPS_BYTELOSS=100` drops all bytes sent from that simulated GPS. The autopilot receives no fresh sensor messages, so its last valid measurement becomes stale. This tests input starvation, not a frozen coordinate repeatedly delivered with fresh validity.
- `SIM_GPS_LAG_MS` delays values through a twenty-sample history. An excessive requested delay uses the oldest stored sample. With the default 5 Hz rate, this cannot model an arbitrarily long freeze. The parameter is not named `SIM_GPS_DELAY` in these pins.

Disable the second receiver with `GPS_TYPE2=0` and keep `SIM_GPS2_DISABLE=1`. The pinned [GPS driver](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_GPS/AP_GPS.cpp) uses a 4,000 ms receive timeout. For an ordinary serial GPS, expiry clears state, removes the backend, and changes status to `NO_GPS`. The adjacent source comment says two seconds, so the executable constant takes precedence over that stale comment. Require both an acknowledged injector setting and observed GPS state degradation. Frozen valid positions with fresh packets remain an explicit coverage gap.

## Evidence and isolation implications

Current [MAVLink field definitions](https://mavlink.io/en/messages/common.html) distinguish host reception times from autopilot `time_boot_ms`. Record host monotonic nanoseconds independently, retain raw MAVLink frames, and derive mode from HEARTBEAT `custom_mode`. `GLOBAL_POSITION_INT.relative_alt` is millimetres; `SYSTEM_TIME.time_boot_ms` is milliseconds; GPS fix type and battery millivolts need explicit interpretation. Packet reception alone does not prove a sensor update.

The pinned [SITL_State.cpp](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_HAL_SITL/SITL_State.cpp) binds RC input to `0.0.0.0`, and [UARTDriver.cpp](https://github.com/ArduPilot/ardupilot/blob/2a3dc4b7bf2507120f7378a7b2fde73185e0c325/libraries/AP_HAL_SITL/UARTDriver.cpp) leaves the TCP listen address zero-initialized. Merely connecting a client to `127.0.0.1` does not make either listener private. Before running, enforce local binding or use an isolated network namespace, and inspect actual process sockets. Keep all unused serial endpoints disabled and prohibit physical-device UART arguments. No simulator process was started as part of this source review.

Compound cases need an observation for each injected fault. A LAND transition caused by one fault does not prove the other occurred. Recovery cases need an observed restored input or failsafe-clear event while confirming that the failsafe mode persists. Negative controls should disable a relevant action or demand a deliberately wrong mode and must cause the evaluator to reject the trace. These methodological checks are laboratory requirements, not facts inferred from the autopilot documentation.
