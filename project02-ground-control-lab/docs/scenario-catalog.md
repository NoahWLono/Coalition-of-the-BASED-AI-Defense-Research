# Scenario catalog and annotation method

These ten incidents use fictional civilian inspection vehicles, locations, actors and observations. Their durations are simulated seconds. They contain no operational thresholds or measured participant results. The scripts contain 134 ordered events and 53 checkpoints, each with 11 expected facts, for 583 literal fact records.

The assistant scenario annotator wrote the scripts and checkpoint expectations from `docs/mission.txt` and `docs/contract.md`. The annotator did not inspect or import the replay engine, interface renderer or evaluator. A serialization step expanded manually entered value/status/timestamp triples into the literal objects in `data/oracle.json`; it did not execute events or calculate expected states. This supplies a separate specification oracle with shared contract assumptions. It is assistant annotation, not human validation or independent empirical confirmation.

The authoring date is 2026-10-17, using the session's stated local date. All numerical values are synthetic and deterministic; there is no random seed because no random generation is used. Labels such as metres, degrees and percent are part of the fictional observations. The neutral calibration unit in the simultaneous-events incident has no physical interpretation.

## Shared interpretation

Every checkpoint requires eleven facts: principal, mode, owner, handover, target, nextActor, telemetry, lastReliable, acknowledgments, alarmGroups and completion.

- All events at a checkpoint second have occurred, in their array order. A pending deadline expires before scripted events at that same second.
- Evidence is known through its exact TTL boundary and stale afterward. Expiry preserves the old value and original evidence timestamp. Explicit null telemetry renders `Unknown` with unknown status at the null event's second. Initial absence would have a null timestamp.
- `lastReliable` retains the latest non-null telemetry as known historical evidence at its original timestamp. It does not certify that old telemetry is current.
- Ownership becomes `Unresolved` with unknown status at acceptance, interruption, conflict or accepted timeout. That timestamp records the state change. Stale owner evidence retains the actor name with stale status. Confirmation and reconciliation establish fresh ownership with a thirty-second TTL.
- The handover timestamp records its latest valid transition. Request sets a target timestamp; acceptance, interruption and timeout retain it. Confirmation, cancellation and reconciliation explicitly clear the target and update its timestamp even if the target was already `None`.
- While a handover is requested, accepted, interrupted, conflicted or timed-out, nextActor uses the handover transition timestamp. In idle, completed or cancelled phases it uses the owner's evidence timestamp and status.
- A receipt records acknowledgment of an active alarm. Multiple actors remain visible, sorted by alarm ID and then actor. Clearing an alarm removes its active receipts and updates the receipt timestamp only if receipts existed. Clearing an unacknowledged alarm changes alarmGroups without changing acknowledgments.
- Invalid events remain in replay history and do not alter the expected facts. Completion requires a known owner, no active alarms and an allowed terminal or idle phase. Each fixture also explicitly observes `No active issue` before its completion event.

The tables below explain the annotation decisions. The JSON oracle holds the full value, status and timestamp for all eleven facts at every listed checkpoint.

## 1. Interrupted quay inspection handover

`interrupted`, Cedar-01 at Fictional East Quay, duration 12 seconds.

Principal issue: Link uncertainty. Required distinguishing evidence includes alarm a1 in group link, Operator B's receipt, the unresolved acceptance/interruption interval and the stale telemetry boundary. The permitted path is idle → requested → accepted → interrupted → completed by Supervisor reconciliation to Operator A. The alarm and principal issue clear at second 8. Completion is then permitted.

| Second | Checkpoint reasoning |
| --- | --- |
| 0 | Operator A owns Inspection; link margin is 82 percent; handover is idle. |
| 3 | Operator B has acknowledged a1 and is the requested next actor; Operator A still owns responsibility. |
| 4 | Operator B accepts. Owner is unresolved and Supervisor must act next. |
| 5 | Interruption preserves unresolved ownership and target Operator B. Five-second telemetry is still known at this exact boundary. |
| 7 | Supervisor restores Operator A and clears the target. Telemetry is stale, with the old value retained as historical evidence. |
| 8 | Alarm a1, its receipt and the principal issue clear; completion is complete. |
| 12 | Mode and telemetry have expired. Completed status does not promote them to current evidence. |

## 2. Stale roof survey evidence

`stale_evidence`, Birch-02 at Fictional Alder Depot, duration 14 seconds.

Principal issue: Observation gap. Required evidence includes owner and telemetry lifetimes of three seconds, absent telemetry after an explicit null report, and the older reliable observation. The permitted path is idle → conflicted → completed by Supervisor. Fresh telemetry, reconciled Operator C ownership and clearance of alarm s1 in navigation permit completion at second 9.

| Second | Checkpoint reasoning |
| --- | --- |
| 0 | Operator C and roof offset 2 metres are known at second 0. |
| 4 | Both owner and current telemetry are stale. Next actor carries the same stale owner evidence. |
| 5 | Telemetry is explicitly unknown at second 5. The last reliable 2-metre observation remains at second 0. |
| 6 | Conflicting responsibility evidence makes owner unresolved. Operator C's receipt of s1 does not resolve it. |
| 9 | Supervisor reconciles to Operator C; roof offset 1 metre is fresh; s1 and the issue clear; completion is complete. |
| 14 | Recovered ownership and the ten-second telemetry observation remain known. |

## 3. Camera alignment alarm cascade

`alarm_cascade`, Maple-03 at Fictional Mill Facade, duration 15 seconds.

Principal issue: Camera alignment fault. The active mapping must distinguish imaging alarms c1, c2, c3 and c5 from storage alarm c4 and inspection alarm c6. These are authored issue groups and do not establish causal relationships. Operator A remains owner throughout; no handover occurs. Clearing all alarms after a corrected gimbal observation and explicit issue clearance permits completion at second 9.

| Second | Checkpoint reasoning |
| --- | --- |
| 2 | All six alarms are active, with their exact group mappings and no receipts yet. |
| 5 | Only c5 has cleared. Receipts for c1, c2 and c4 remain; their latest evidence timestamp is second 4. |
| 9 | All alarms and receipts clear, gimbal offset becomes 0 degrees, and completion is complete. |
| 15 | The corrected observation remains known and the cleared state persists. |

## 4. Two acknowledgments and one owner

`conflicting_receipts`, Willow-04 at Fictional Canal Walkway, duration 12 seconds.

Principal issue: Battery estimate disagreement. Both Operator A and Operator B receipts for r1 must remain visible. Their apparent competing involvement does not create a handover or an ownership conflict by itself. Ownership stays with Operator A and phase stays idle. Acceptance without a matching request is rejected. A corrected battery estimate and clearance of r1 and the issue permit completion at second 6.

| Second | Checkpoint reasoning |
| --- | --- |
| 2 | Operator A has acknowledged r1 and remains owner. |
| 3 | Receipts from both operators are present, sorted A then B. Ownership remains Operator A. |
| 4 | Operator B's acceptance for a never-requested handover is rejected. Facts remain unchanged. |
| 6 | The battery estimate changes from 48 to 51 percent; r1, both receipts and the issue clear. |
| 12 | The completed incident retains Operator A and the corrected observation. |

## 5. Conflicting responsibility reports

`ownership_conflict`, Hazel-05 at Fictional Orchard Viaduct, duration 12 seconds.

Principal issue: Responsibility report mismatch. Console and shift reports name different owners. The permitted path is idle → conflicted → completed by Supervisor reconciliation. A later owner observation cannot bypass recovery. Alarm o1 in handover and Operator C's receipt are additional facts, not evidence of an accepted transfer. Supervisor restoration of Operator B and clearance of o1 and the issue permit completion at second 6.

| Second | Checkpoint reasoning |
| --- | --- |
| 1 | Conflicting reports make responsibility unresolved and Supervisor the next actor. |
| 2 | An attempted owner observation naming Operator C is rejected. |
| 4 | Operator C has acknowledged o1; ownership remains unresolved. |
| 6 | Supervisor reconciles Operator B, then o1 and the issue clear and completion is complete. |
| 12 | The reconciled owner and cleared state persist. |

## 6. Accepted handover expires unconfirmed

`accepted_timeout`, Rowan-06 at Fictional Waterworks Fence, duration 12 seconds.

Principal issue: Shift handover pending. The permitted path is idle → requested → accepted → timed-out → completed by Supervisor reconciliation. Confirmation at the deadline is late because timeout occurs first. A replacement request is invalid while ownership is unresolved. Supervisor reconciles to Operator B and clears the principal issue at second 8; there are no alarms to clear.

| Second | Checkpoint reasoning |
| --- | --- |
| 2 | Operator B accepts. Responsibility is unresolved and Supervisor is next. |
| 5 | Timeout precedes confirmation. Target Operator B remains diagnostic information; owner remains unresolved with timeout evidence at second 5. |
| 6 | A replacement request from Operator A is rejected because there is no known owner. |
| 8 | Supervisor reconciles to Operator B, clears the target and issue, and completion is complete. |
| 12 | The recovered ownership and completed status persist. |

## 7. Acceptance at the request deadline

`requested_timeout`, Ash-07 at Fictional Meadow Solar Canopy, duration 12 seconds.

Principal issue: Transfer deadline pending. The permitted path is idle → requested → timed-out → completed by Supervisor reconciliation. Unlike an accepted timeout, this timeout preserves known source ownership. Operator D's same-second acceptance is rejected. Supervisor re-establishes Operator C at second 6; the later explicit issue clearance permits completion at second 8.

| Second | Checkpoint reasoning |
| --- | --- |
| 1 | Operator C owns responsibility while Operator D is the requested next actor. |
| 5 | Timeout occurs first. Operator C remains owner, Supervisor is next and the delayed acceptance has no effect. |
| 6 | Reconciliation confirms Operator C with fresh evidence and clears the target. The issue is still active and completion remains incomplete. |
| 8 | Explicit principal clearance permits completion. |
| 12 | The resolved request and completed incident persist. |

## 8. Cancelled handover with delayed receipt

`cancelled_receipt`, Elm-08 at Fictional Brook Footbridge, duration 12 seconds.

Principal issue: Camera review requested. The permitted path is idle → requested → cancelled. Source cancellation retains Operator A and clears the target. A delayed receipt of k1 in imaging is valid; delayed acceptance of the cancelled offer is rejected. Alarm and issue clearance permit completion in the cancelled phase at second 6.

| Second | Checkpoint reasoning |
| --- | --- |
| 2 | Operator A cancels, remains owner and is next actor with the original owner timestamp. |
| 3 | Operator B acknowledges k1; this receipt does not revive the handover. |
| 4 | Operator B's delayed acceptance is rejected. |
| 6 | Alarm, receipt and issue clear; completion is complete while handover remains cancelled. |
| 12 | The completed incident preserves cancellation and original ownership. |

## 9. Ordered events at the calibration pause

`simultaneous_events`, Pine-09 at Fictional Civic Hall Roof, duration 10 seconds.

Principal issue: Calibration pause. At second 2, the array order is request, acceptance, alarm q1, Operator A receipt, q1 clear, Operator B receipt attempt and confirmation. The receipt after clear is rejected. The permitted path is idle → requested → accepted → completed, all within that second. Absent telemetry and alarm q2 in evidence appear at second 3. Fresh telemetry plus alarm and issue clearance permit completion at second 6.

| Second | Checkpoint reasoning |
| --- | --- |
| 0 | Operator A owns the incident and calibration error 3 units is known. |
| 2 | Operator B owns the confirmed transfer. No alarm or receipt remains, and both empty-state change timestamps are second 2. |
| 3 | Current telemetry is explicitly unknown; historical 3-unit evidence remains, and q2 is active. |
| 6 | Calibration error 0 units is fresh and q2 clears. Because q2 had no receipts, acknowledgments retains timestamp 2 while alarmGroups changes at 6. |
| 10 | Confirmed ownership, recovered evidence and completion persist. |

## 10. Confirmed handover and separate mode change

`successful_handover`, Juniper-10 at Fictional Lakeside Greenhouse, duration 12 seconds.

Principal issue: Inspection resumption pending. The permitted path is idle → requested → accepted → completed through supervisory confirmation. The control mode remains Survey hold until a separate observation at second 5. This prevents responsibility transfer from implying a mode change. Operator E ownership, the Inspection observation, and clearance of unacknowledged alarm u1 and the principal issue permit completion at second 8.

| Second | Checkpoint reasoning |
| --- | --- |
| 1 | Operator D remains owner, Operator E is next actor, and mode is Survey hold. |
| 2 | Acceptance makes owner unresolved and Supervisor next; mode remains Survey hold. |
| 3 | Supervisor confirms Operator E. Target clears, but mode still remains Survey hold. |
| 5 | An explicit observation changes mode to Inspection and telemetry to progress 95 percent. Ownership evidence remains at second 3. |
| 8 | Alarm u1 and the issue clear; completion is complete. No receipt existed, so acknowledgments retains timestamp 0. |
| 12 | Ownership confirmation and mode observation retain their distinct timestamps. |

## Annotation checks and limits

Local structural checks parse both JSON files, confirm exactly ten unique scenario IDs, verify nondecreasing event times and bounded durations, and require a one-to-one match between all 53 declared checkpoints and oracle records. Each oracle record must contain exactly the eleven contract keys, with literal string values, allowed statuses and valid timestamp types. The check also confirms that every scenario reaches an annotated completed final checkpoint and that its scripted principal clearance precedes its completion event.

These checks validate fixture structure. The separate engine and DOM comparisons are reported by the implementation owner. Agreement with these annotations cannot establish field safety, causal alarm grouping, participant workload, response speed or human usability. The fixtures are bounded examples of the declared state model.
