# Optional future task materials

Status: unused templates. No participant answers, observations, completion times, or workload measurements have been collected. Use these materials only after completing [participant-protocol.md](participant-protocol.md). Blank fields are intentional and do not represent missing results from a completed study.

Separate the participant pages from the facilitator pages before use. Participants receive the introduction, task cards, and blank response sheet. The facilitator alone receives the checkpoint manifest, oracle key, and observation sheet. Do not include expected answers in participant materials or expose the oracle through the task packet.

## Participant introduction

You will inspect fictional civilian inspection incidents in three versions of a local interface. The interface cannot control an aircraft. The events are scripted and the clock shows simulated seconds.

Please answer using the information available at the stated checkpoint. You may open details. If information is stale, unknown, unresolved, or unavailable, say so. You do not need to guess. You may ask for the instructions again, skip a question, request a break, or stop. Tell the facilitator if the presentation or controls need an adjustment. You do not need to explain a disability or disclose a diagnosis.

An alarm acknowledgment records receipt. Accepting a handover is a different event, and ownership can remain unresolved pending confirmation. Control mode is separate from responsibility. Historical evidence keeps its original timestamp and does not establish the current situation.

## Participant task cards

The facilitator supplies the incident ID and replay checkpoint for each card. Answer all parts listed for that card. Do not change incident, view, or replay time unless the card explicitly asks you to compare checkpoints.

| Task ID | Prompt |
| --- | --- |
| T1: principal issue | What is the principal issue at this checkpoint? Give its evidence state and timestamp. If the issue has been cleared or is unknown, state that. |
| T2: related alarms | List the active alarm IDs and their authored groups. Which alarms share a group and which have a different group? Give the evidence state and timestamp for the grouping record. A group is a scripted relationship; do not infer a physical cause from the grouping alone. |
| T3: owner and next actor | Who currently has responsibility, and who is responsible for the next action? Give the evidence state and timestamp for each answer. If current responsibility cannot be established, say so and distinguish that from a stale report of an actor. |
| T4: mode and handover | What is the current control mode? What handover phase and target are shown? Give the evidence state and timestamp for each. Describe receipt acknowledgments separately from a handover acceptance. |
| T5: current and historical evidence | Report the current telemetry record with its evidence state and timestamp. Then report the last reliable observation with its evidence state and original timestamp. Explain whether it establishes a current observation at this checkpoint. |
| T6: receipts | Which actors have acknowledged each active alarm? Give the evidence state and timestamp for the receipt record. What, if anything, does the responsibility evidence establish separately? Give the owner record's evidence state and timestamp as well. |
| T7: completion | Does the script mark this incident complete at this checkpoint? Give the state and timestamp of the completion record. Use the supplied incident completion criteria to identify any criteria still unmet or any evidence you cannot establish. |
| T8: interrupted handover comparison | At the first specified checkpoint, report the owner, next actor, handover phase, and target, including evidence state and timestamp. Repeat at the second checkpoint. What evidence changed between them? |

For T7, give the participant only the independently authored narrative completion criteria, without checkpoint answers or the oracle's expected values. For T8, the facilitator supplies the same interruption and recovery checkpoint pair in each view. No operational action is requested.

## Blank participant response sheet

Duplicate this sheet once per task and checkpoint. For T8, use one copy for each of its two checkpoints. The participant should not write a name, email address, employer, or personal operational details.

| Field | Entry |
| --- | --- |
| Study code supplied by facilitator | ____________________ |
| View code | ____________________ |
| Incident ID | ____________________ |
| Checkpoint, simulated seconds | ____________________ |
| Task ID | ____________________ |
| Optional choice | Answer / Skip / Break / Stop |

| Requested fact | Answer or unavailable | Known / stale / unknown | Evidence timestamp, simulated seconds |
| --- | --- | --- | --- |
| ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ |

Explanation requested by the task: ________________________________________

Evidence that remains unavailable or unclear: ______________________________

Optional comment about the presentation, without personal details: __________

## Facilitator preparation only

The following pages contain study setup and scoring fields. Exclude them from the participant packet. They contain no completed observation records.

Freeze the version of `data/scenarios.json`, `data/oracle.json`, [contract.md](contract.md), and this packet. For each incident, select the same checkpoint set for all three views. Include checkpoints that expose stale evidence, alarm cascades, conflicting receipts and reports, cancelled or timed-out handovers, and the unresolved and reconciled intervals of the interrupted handover. Use the oracle's literal fact records to complete the answer key. Do not derive expected answers from `replay`, the renderer, screenshots, or a developer's assertion of what the interface should say.

An oracle key provides specification-based scoring, not empirical proof about people. Record the oracle's assistant authorship and the identity or role of any later reviewer. If an oracle row conflicts with the narrative rules, resolve the conflict before using the item and freeze the corrected version. Do not change a key after seeing responses without recording the change and applying the same correction to every affected response.

## Blank checkpoint manifest

The base incident order below matches the ten synthetic script IDs. Fill checkpoint and task fields from the frozen study plan. The participant must see the same questions and checkpoint times for an incident in every view. Add rows only through a recorded protocol revision.

| Base index | Incident ID | Checkpoint(s), simulated seconds | Task IDs | Oracle row locator(s) |
| --- | --- | --- | --- | --- |
| 0 | interrupted | __________ | __________ | __________ |
| 1 | stale_evidence | __________ | __________ | __________ |
| 2 | alarm_cascade | __________ | __________ | __________ |
| 3 | conflicting_receipts | __________ | __________ | __________ |
| 4 | ownership_conflict | __________ | __________ | __________ |
| 5 | accepted_timeout | __________ | __________ | __________ |
| 6 | requested_timeout | __________ | __________ | __________ |
| 7 | cancelled_receipt | __________ | __________ | __________ |
| 8 | simultaneous_events | __________ | __________ | __________ |
| 9 | successful_handover | __________ | __________ | __________ |

Required coverage check before freezing: T1 through T7 across the scored set; T3 at an unresolved ownership checkpoint and at recovery; T5 with stale current telemetry and with explicitly unknown telemetry; T2 during the cascade; T6 with multiple or delayed acknowledgments; T8 for the interrupted handover pair. Repeat each chosen incident/checkpoint/task item in all three views. Choose the final number of items before estimating burden or sample size.

## Blank facilitator oracle key

Duplicate per incident/checkpoint/task. Populate before participants encounter the task. This sheet is not a participant answer form.

| Key field | Value to enter from the frozen specification |
| --- | --- |
| Scenario and oracle hashes | ____________________ |
| Incident ID | ____________________ |
| Checkpoint, simulated seconds | ____________________ |
| Task ID | ____________________ |
| Oracle locator: scenarioId and at | ____________________ |
| Oracle rationale | ____________________ |
| Independent narrative completion criteria for T7 | ____________________ |
| Key preparer and review status | ____________________ |

| Required oracle fact key | Expected value | Expected evidence state | Expected timestamp | Accepted paraphrases fixed before collection |
| --- | --- | --- | --- | --- |
| ____________________ | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ | ____________________ |
| ____________________ | ____________________ | ____________________ | ____________________ | ____________________ |

For T1 use `principal`; T2 uses `alarmGroups`; T3 uses `owner` and `nextActor`; T4 uses `mode`, `handover`, and `target`; T5 uses `telemetry` and `lastReliable`; T6 uses `acknowledgments` and `owner`; T7 uses `completion` plus the independent narrative completion criteria; T8 uses `owner`, `nextActor`, `handover`, and `target` at each checkpoint. Score factual components against the key before considering explanatory comments. Do not require a participant to invent a value for an unknown fact.

Task completion means that the response has been submitted, skipped, or stopped according to the protocol. A correct response matches the required oracle facts and requested explanation. Incident completion is a separate scripted condition. The interface's completion label alone cannot replace the independent narrative criteria when scoring T7.

## Blank session allocation and setup sheet

| Field | Entry |
| --- | --- |
| Study code | ____________________ |
| View-order cell V1 through V6 | ____________________ |
| Incident rotation r, 0 through 9 | ____________________ |
| Assigned block orders recorded before session | ____________________ |
| Frozen app, scenario, oracle, and task versions | ____________________ |
| Consent record present in separate storage | Yes / No |
| Comprehension check and any retraining completed | ____________________ |
| Participant-chosen input method and necessary display adjustments | ____________________ |
| Optional measures consented to | None / ____________________ |
| Planned breaks and stop rule | ____________________ |
| Initial viewport, focus policy, and disclosures closed | ____________________ |

Do not record a diagnosis or the reason for an accommodation. A session cannot begin if consent or the predeclared comprehension rule is unmet.

## Blank facilitator observation sheet

Duplicate per task and checkpoint. Keep literal observations separate from interpretation. Record a technical failure or assistance according to the predefined codes. Avoid comments about personality, competence, or inferred disability.

| Field | Entry |
| --- | --- |
| Study code, block, and incident position | ____________________ |
| View, incident ID, checkpoint, and task ID | ____________________ |
| Prior exposures to this incident | ____________________ |
| Confirmed replay paused and all disclosures initially closed | ____________________ |
| Submitted / skipped / stopped / technically invalid / not asked | ____________________ |
| Required atomic facts and fully correct facts | ____________________ |
| Owner or next-actor error, if any | ____________________ |
| Stale or historical evidence presented as current in the response | ____________________ |
| Disclosure activations | ____________________ |
| Replay or checkpoint navigation actions | ____________________ |
| View changes | ____________________ |
| Keyboard navigation count, only if predefined | ____________________ |
| Help requests and standardized assistance given | ____________________ |
| Break or interruption code | ____________________ |
| Verbatim brief task observation, without personal details | ____________________ |
| Scorer, key version, and adjudication status | ____________________ |

Timing and workload fields are deliberately absent from this default sheet. Add them only after their definitions, consent choices, instrument or clock procedure, and analysis rules have been finalized. A replay timestamp is a scenario coordinate. It is not a measured response time. Disclosure counts cannot establish workload or a human performance benefit.

## Blank factual scoring sheet

| Study code and item ID | Oracle fact key | Value correct, 0/1 | Evidence state correct, 0/1 | Timestamp correct, 0/1 | Entire fact correct, 0/1 | Missing or invalid code | Scoring note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| __________ | __________ | __________ | __________ | __________ | __________ | __________ | __________ |
| __________ | __________ | __________ | __________ | __________ | __________ | __________ | __________ |
| __________ | __________ | __________ | __________ | __________ | __________ | __________ | __________ |

Use missing or invalid codes from the frozen protocol rather than forcing every blank to 0. Record any scoring disagreement and its resolution. The table supplies no findings until consenting participants have produced actual responses under an approved, finalized procedure.
