# Executed release comparison

State: complete; 58 of 58 planned simulator runs have results.

This report is derived from recorded SITL evidence. It establishes only the listed assertions for this simulator, vehicle model and configuration. Assistant-authored scenarios and trace inspection are not qualified human certification.

## Scenario results

| Scenario | 4.5.6 outcomes | 4.5.7 outcomes | LAND response range, simulation s |
| --- | --- | --- | --- |
| 01-gcs-loss | 0s offset: PASS; 0.7s offset: PASS; 1.4s offset: PASS | 0s offset: PASS; 0.7s offset: PASS; 1.4s offset: PASS | 2.900 to 3.298 |
| 02-battery-low | 0s offset: PASS; 0.7s offset: PASS; 1.4s offset: PASS | 0s offset: PASS; 0.7s offset: PASS; 1.4s offset: PASS | 3.098 to 3.202 |
| 03-rc-loss | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | 0.998 to 1.002 |
| 04-gcs-recovery | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | 3.002 to 3.298 |
| 05-rc-recovery | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | 0.998 to 1.002 |
| 06-battery-recovery | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | 3.098 to 3.202 |
| 07-gcs-transient | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | no LAND assertion |
| 08-battery-transient | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | no LAND assertion |
| 09-gps-stale | 0s offset: PASS; 0.7s offset: PASS; 1.4s offset: PASS | 0s offset: PASS; 0.7s offset: PASS; 1.4s offset: PASS | 7.798 to 7.902 |
| 10-gcs-rc-compound | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | 0.998 to 1.002 |
| 11-gcs-battery-compound | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: FAIL | 2.898 to 3.098 |
| 12-gps-rc-compound | 0s offset: PASS; 0.7s offset: PASS | 0s offset: PASS; 0.7s offset: PASS | 0.902 to 1.002 |

Response values use the last SYSTEM_TIME sample at packet reception. Clock sampling is 0.1 s and heartbeat sampling is 0.2 s; small latency differences within those intervals do not establish a release regression. The DataFlash crosscheck uses onboard microsecond timestamps.

## Configuration and controls

Full parameter snapshots compared for 12 primary scenario pairs. Pairs with any differing value: 0. Exact differences, if present, remain in comparison.json.

- 4.5.6 disabled GCS action: FAIL. Qualified expected mismatch: True. This control retains the enabled-action expectation.
- 4.5.7 disabled GCS action: FAIL. Qualified expected mismatch: True. This control retains the enabled-action expectation.
- 4.5.6 wrong-mode replay: FAIL. Qualified targeted mismatch: True. The original packets were unchanged.
- 4.5.7 wrong-mode replay: FAIL. Qualified targeted mismatch: True. The original packets were unchanged.

## Resources and cleanup

Sum of scenario wall times: 1783.2 s. Largest recorded child maximum RSS: 31.3 MiB. Cleanup or remaining-listener violations: 0.

## Unresolved outcomes

- 4.5.7/11-gcs-battery-compound/schedule-0.7: FAIL; Observed status text does not include the required text
All full-suite gates resolved: False.
