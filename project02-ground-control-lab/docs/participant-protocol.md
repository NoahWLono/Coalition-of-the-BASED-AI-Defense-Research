# Optional future participant protocol

Status: draft for a possible future study. No people have been recruited, no consent has been obtained, and no human responses, completion times, workload scores, or participant findings have been collected for this laboratory. The current project checks synthetic scenarios and interface behavior. This document does not authorize recruitment or data collection.

The proposed study would compare the chronological alarm list, incident-grouped view, and handover-state view while people answer questions about the same ten fictional incidents. Its purpose is to examine whether people can recover the facts shown by each view. It would not establish fitness for operational use, flight safety, operator qualification, or regulatory certification.

## Decisions required before recruitment

The future study owner must complete and freeze the following record before contacting anyone. Any applicable institutional review process remains the study owner's responsibility; this draft asserts no ethics approval.

| Decision | Record before recruitment |
| --- | --- |
| Study owner and participant contact route | Unassigned |
| Review and approval requirements for the setting | Unresolved |
| Recruitment setting, adult eligibility, and compensation, if any | Unset; no actual contacts or invitations |
| Intended participant population and inclusion rationale | Unset |
| Feasible session length, breaks, and maximum exposure | Unmeasured; establish through separately consented feasibility work |
| Sample size and allocation plan | Unresolved; the schedule cells below are not a sample-size recommendation |
| Primary comparison, smallest effect of interest, and analysis plan | Unset |
| Power or precision justification | Unresolved; no assumed effect or fabricated variance |
| Frozen app, scenario, oracle, and task-material versions | Record revision identifiers and file hashes |
| Checkpoints and scoring key | Freeze from the separate oracle before any scored session |
| Data fields, storage owner, access, retention, and deletion date | Unset |
| Withdrawal route and last date for deletion of linked records | Unset |
| Consent wording and accessible formats | Complete and review before use |

A feasibility exercise can assess whether the proposed session is tolerable and whether the questions are understood. It still requires informed consent. Its observations must be labelled as feasibility data. They cannot be described as a powered comparison of the views. Choose the confirmatory sample size only after the intended estimand, variability assumptions, participant constraints, and repeated-measures design have been specified.

## Recruitment, consent, and participant choice

Use voluntary recruitment through a future approved route. This repository contains no contact list and this project has sent no invitations. Recruitment text should describe a fictional interface exercise, the expected activities, the eventual verified duration estimate, compensation terms if any, and the right to decline. Avoid recruitment arrangements that make a person's employment, assessment, or access to services depend on participation.

Before consent, explain that the application cannot control a vehicle and that its events are scripted. The tasks involve reading alarms, finding evidence, and reporting responsibility at fixed replay times. Explain the data fields, who will see them, storage location, retention period, and withdrawal cutoff in language the person can review at their own pace. Do not promise complete anonymity while a withdrawal code still links their records.

Participation is optional. A person may skip any question, take a break, stop the session, or withdraw without giving a reason. Give the participant a private withdrawal code and the agreed contact route. Before the stated cutoff, the study owner can locate and delete the linked response records. After identifiers and the linkage have been irreversibly removed or results aggregated, removal of one person's contribution may no longer be possible. Explain that limit before consent and record the actual cutoff, rather than leaving a blank in a form used with participants.

Ask whether the person wants changes to text size, contrast, motion, input method, audio presentation, instructions, or breaks. Disability disclosure and diagnoses are optional and unnecessary for this task. Participants choose whether to describe an access need. Record only the accommodation necessary to interpret the task conditions, and only with permission. A person's chosen assistive technology is part of their session setup. Do not remove it to create uniformity or treat its use as a participant error.

Obtain separate choices for participation, optional comments, and any optional timing or workload data. The default plan excludes audio, video, screen recording, biometric data, employment details, and clinical information. Any later proposal to collect these requires revised participant information and explicit consent before collection. A participant can decline optional measures while completing the factual questions, if the finalized study design permits that option.

## Data minimization and storage

Keep consent and contact records separate from task responses and outside this public-ready source tree. Use a study code in task records. Retain a linkage only until the announced withdrawal cutoff. While the linkage exists, call the records pseudonymized. Call released records anonymized only after checking that free text and combinations of fields cannot identify a participant.

The proposed minimum task record is study code, schedule cell, view, incident ID, checkpoint, task ID, response, score, disclosure count, assistance or interruption code, and session configuration needed to interpret access. Omit exact wall-clock dates, names, contact details, and unrestricted device logs from analysis exports. Optional comments should be brief and screened for identifying material before sharing. Do not upload participant data to model services or external analytics under this draft.

Before recruitment, name the people with access, storage protection, retention deadline, backup deletion procedure, and aggregate reporting rules. Report small categories cautiously so optional access information does not identify someone. Do not collect a demographic field merely because a template offers space for it.

## Training and comprehension

Use the same written introduction and equivalent practice in each view. Before scored trials, teach the controls for selecting a view, expanding details, pausing, and moving to a checkpoint. Practice must use a separately prepared, unscored example with its own truth key; the ten scored incidents must not provide training answers.

Teach the following terms in the participant's preferred accessible format:

- Acknowledging an alarm records receipt. It does not accept a handover or change control ownership.
- Acceptance is a handover stage. In this laboratory, ownership becomes unresolved after acceptance until the required supervisory confirmation or reconciliation establishes an owner.
- Control mode and responsible actor are separate facts.
- Known, stale, and unknown describe evidence state. A stale last report cannot establish the current actor or current telemetry.
- The last reliable observation is historical evidence with its original timestamp. It does not become a current observation because it remains visible.
- Alarm groups are authored relationships in the fictional script. A shared group alone does not prove a physical cause.

Ask the person to explain receipt versus acceptance, current versus historical evidence, and what to answer when ownership is unresolved. The facilitator checks understanding against the training key, offers the same explanation when needed, and records that retraining occurred. This comprehension check assesses whether instructions are usable; it is not an operator certification or a medical or cognitive assessment. If comprehension remains unclear, offer more practice or end the session according to the predeclared rule. Record no scored trial until that rule is satisfied.

## Counterbalancing three views across ten incidents

Use A = chronological, B = grouped, and C = handover. Each participant would encounter all ten incidents in each view, for 30 incident presentations. Each presentation uses the same frozen checkpoint set and task prompts for that incident. The number of questions depends on the checkpoint manifest and must be included in the eventual burden estimate.

Allocate view blocks across the six orders below. Each order contains all three views once. A complete, equally filled cycle balances view position and ordered adjacent view pairs.

| View-order cell | Block 1 | Block 2 | Block 3 |
| --- | --- | --- | --- |
| V1 | A | B | C |
| V2 | A | C | B |
| V3 | B | A | C |
| V4 | B | C | A |
| V5 | C | A | B |
| V6 | C | B | A |

Freeze the incident base order as the ten rows in the facilitator manifest in [task-materials.md](task-materials.md). Assign an incident rotation r from 0 through 9. In zero-based block b, present base incident at index `(j + r + 3*b) mod 10` at zero-based position j. This changes the starting incident between blocks. With all ten rotations equally represented for each view-order cell, each incident occupies each position in each block equally often. Record the actual order before the session.

The six view orders and ten rotations define 60 allocation cells. This is a schedule, not a requirement to recruit 60 people or a power calculation. Before recruitment, choose a feasible allocation method, record any randomization seed if used, and state the balance attainable at the planned sample size. Assignments must not depend on observed task scores. Report incomplete cells and withdrawals without silently replacing them based on performance.

Repeated exposure to the same incident can reveal its answer. View order can also interact with fatigue, training, or familiarity with disclosures. Counterbalancing reduces some order imbalances but does not erase these carryover effects. Do not reveal the answer key or corrective task feedback between scored blocks. Allow breaks at the same planned opportunities and whenever requested. Record block, incident position, prior exposure, help, and interruptions. Prespecify how these enter analysis, including a descriptive comparison of first exposure if feasible. A claim about first-use performance must be based on first-exposure observations.

## Session procedure

1. Verify the frozen versions and complete the facilitator answer key from `data/oracle.json`. Resolve oracle ambiguities before starting. The renderer and developer's expected screen content cannot define correct answers.
2. Provide participant information, answer questions, obtain the necessary consent choices, and agree on accommodations and breaks. Confirm that the participant can stop without explanation.
3. Complete standardized training and the comprehension check. Keep the training key out of scored task materials.
4. Load the assigned view and incident. Pause at the manifest checkpoint, close all fact disclosures, use the same viewport and initial focus policy, and confirm the displayed simulated time. If an accommodation changes that setup, record the agreed condition.
5. Present the task card without hints about where its answer is located. Permit the participant to inspect the view and say that a fact is unknown, unresolved, or unavailable. Log only the agreed data. Use the same help policy in every view.
6. End the task when the person submits an answer, skips it, requests a stop, or reaches a predeclared limit. Apply no invented time limit. Record a technical interruption separately from a wrong answer.
7. Repeat the frozen checkpoint set and incident order, including the planned breaks. Reset the replay and disclosures between presentations so a prior expanded section does not change the starting condition.
8. Debrief after all scored blocks or on withdrawal. Explain that interface difficulties are useful design evidence, confirm the withdrawal route and cutoff, and offer the approved contact information.

The participant answers questions about the script. They are not asked to make operational flight decisions. Replay controls affect the local mock only. A participant's response cannot mark the scenario complete or change the oracle.

## Predefined endpoints and scoring

The proposed primary endpoint is factual accuracy at the frozen checkpoints. Each scored fact is a value, evidence state, and timestamp from the separate oracle. Define accepted paraphrases before collection. A fully correct fact requires all requested components; report component scores separately if useful. Preserve unknown and stale as valid answers when the oracle requires them. A response of a named actor without the required stale qualifier is not a correct claim of current ownership.

The task key maps principal issue to `principal`, current control mode to `mode`, responsibility to `owner` and `nextActor`, handover to `handover` and `target`, current observation to `telemetry`, historical observation to `lastReliable`, alarm relationships to `alarmGroups`, receipts to `acknowledgments`, and completion to `completion`. Scenario completion additionally requires the independently specified completion condition. Acknowledgment alone cannot satisfy it. For an interrupted handover, score the unresolved interval and the recovery checkpoint separately.

Use an atomic fact score of 1 for correct and 0 for incorrect. Record skipped, withdrawn, technically invalid, and not asked as separate codes. Keep wrong answers distinct from missing responses. Predefine denominators and treatment of missing data before analysis. Do not convert a withdrawn session into failures. A high total score cannot conceal a wrong ownership claim: report owner, next actor, and stale-evidence errors separately.

Interaction steps are a separate descriptive endpoint. Count disclosure activations, replay or checkpoint navigation, view changes, and requests for help as separate categories. Record the initial disclosure state. The minimum required disclosure count from interface inspection is a property of that configured view. It is not a person's observed step count, completion time, or workload. A keyboard Tab press and a mouse click are different actions; preserve modality and counting definitions rather than combining them into an unexplained total.

Completion time and perceived workload are optional future endpoints. This project has measured neither. Before adding timing, define the start event, submission event, clock source, exclusions, pause policy, and treatment of assistive technology and interruptions. Simulated scenario seconds do not measure human completion time. Before adding workload, select a specified instrument, verify its source and use conditions, freeze its scoring and administration, and obtain the relevant consent choice. Do not invent workload scores from errors, step counts, or developer impressions.

Repeated tasks from one participant are correlated. A future analysis must respect that dependence, describe order and incident effects, and distinguish exploratory results from the preregistered comparison. Identify who scored responses and which judgments were adjudicated. This assistant-authored protocol and oracle do not constitute human review or empirical validation. Any benefit concerning speed, workload, situational understanding, or real-world safety remains a hypothesis until supported by appropriate observations.

## Readiness check

Do not use these drafts with participants until the unresolved decisions are completed, the participant-facing pages are separated from the facilitator key, the current interface passes the project's semantic checks, and an accessible unscored practice example exists. Archive the finalized protocol and deviations with the study records. Keep those records outside this source repository unless a later explicit decision establishes a suitable location and permissions.
