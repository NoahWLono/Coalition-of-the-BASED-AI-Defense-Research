# Comparison and verification report

The ten fictional incidents replay deterministically, and all three designs match the separately authored checkpoint facts. The final checks found no factual difference between the designs. Their concrete differences are information placement, alarm organization and the disclosures needed to reach task answers.

The later theme update adds Dark, Light and System choices without changing the reducer, fixture data, renderer, replay controls or exports. All 31 current Node tests passed, including five theme-preference tests, and the model/render evaluator again checked 1,749 records with zero mismatches. Current palette checks are recorded in [contrast.json](../evidence/contrast.json). The browser findings and screenshots in this report come from the original light-theme delivery; the browser suite was not rerun for this update.

## Evidence and scope

The fixtures contain 134 scripted events and 53 checkpoints. Each checkpoint specifies 11 value/state/timestamp records. The Node evaluator checked 1,749 rendered records across the three variants with zero mismatches. The Chromium evaluator independently read the actual answer text, state words and timestamps for the same 1,749 records. It checked every initially closed disclosure after opening it, as well as active alarm labels, declared group labels, group headings and group counts.

The original Node suite passed 26 tests. Replaying all 133 integer-second positions across the ten incidents produced identical state on repeated evaluation; seeking and resetting also matched fresh replay. Browser event-history hashes matched across designs at all 53 checkpoints. View selection therefore did not change the tested event order or simulated timing.

The oracle annotator used the narratives and declared protocol without reading the reducer or renderer. Expected tuples were entered manually and serialized into literal JSON. The oracle, labels and review were assistant-produced. This provides separation from implementation, while shared assumptions remain a limitation. It is not empirical evidence from people.

Evidence files are [evaluation.json](../evidence/evaluation.json), [browser-report.json](../evidence/browser-report.json), [unit-tests.txt](../evidence/unit-tests.txt), [correctness-matrix.csv](../evidence/correctness-matrix.csv) and [browser-correctness-matrix.csv](../evidence/browser-correctness-matrix.csv). The browser report records Chromium 151.0.7922.34, zero page errors and zero external requests during the test. Host, versions, units and freshness parameters are in [environment.json](../evidence/environment.json).

## Observed design differences

Visible means exposed in the document without opening a disclosure. It does not guarantee placement above the viewport fold. Obscured means inside a closed, keyboard-accessible native disclosure. Omitted means absent. Initial counts apply to the eleven evaluated fact records, not to every line of prose or alarm detail.

| Design | Exposed facts per checkpoint | Obscured facts per checkpoint | Omitted | Purpose and concrete cost |
| --- | ---: | ---: | ---: | --- |
| Chronological alarms | 7 | 4 | 0 | Arrival order is prominent. Principal issue, group mapping, next actor and historical telemetry require the context disclosure. |
| Incident groups | 8 | 3 | 0 | Authored issue groups and principal issue are prominent. Handover phase, target and next actor require the handover disclosure. |
| Handover state | 9 | 2 | 0 | Ownership and next actor appear together with transfer phase and target. Alarm receipts and group mappings require the alarm disclosure. |

Across 53 checkpoints, the respective exposed/obscured counts were 371/212, 424/159 and 477/106. Every record matched the oracle regardless of placement. These counts describe these specific implementations and do not rank the design families generally.

At interrupted-handover second 5, a keyboard-only script selected the checkpoint and each design, then located owner, next actor, principal issue and last reliable observation. Chronological required one disclosure activation for next actor, issue and history. Grouped required one for next actor. Handover required zero. From the selected design control, reaching the relevant disclosure took eight Tab presses in the first two variants. The script used actual keyboard events; it did not focus the target programmatically. These counts are reproducible interaction paths, not participant completion times, workload scores or estimates of cognitive effort.

The alarm-cascade script creates a bounded six-alarm burst. Four alarms share the declared imaging group; storage and inspection alarms remain separate. The group view exposes that partition, while chronological retains arrival order. At second 5, one imaging alarm has cleared and five alarms remain. The fixture does not establish a physical cause or performance under large operational alarm loads.

## Fault detection and edge cases

Wrong ownership and wrong grouping were injected into state before rendering each of the three designs: all six checks detected the changed facts. A stale owner promoted to current was also detected. Two further DOM-only regressions hide the owner value or replace the visible group heading while leaving model metadata intact; both are detected by the corrected browser audit. Red/green evidence and review disposition are in [review.md](../evidence/review.md).

The scenarios and tests cover receipt without acceptance, multiple receipts, stale owner and telemetry evidence, explicit unknown observations, ownership conflicts, interruption after acceptance, requested and accepted timeouts, cancellation with delayed receipt and acceptance, and simultaneous script events. Timeout is processed before acceptance or confirmation at the exact deadline. An invalid transition remains rejected in history. Reset while playing pauses replay and removes future state.

Every display value has a freshness state and an evidence timestamp, including explicit null timestamps for evidence never observed. Unknown ownership is shown as Unresolved. A stale owner is labelled as a previous observation, and nextActor inherits that stale state when no new handover action establishes another responsible actor. Historical telemetry remains labelled historical even when the current record becomes unknown.

All four UI downloads were exercised. Scenario events and checkpoints matched the script; exported state and trace matched the current replay; the CSV was byte-equal to the generated matrix. The matrix is a saved evaluation artifact. Editing local code or scripts requires rerunning `npm run evaluate` before exporting an updated matrix.

## Limits and next step

This is a bounded interface and protocol laboratory. The finite-state rules are fictional, freshness thresholds are illustrative, and principal clearance is a scenario-authoring requirement in addition to the engine's generic completion guard. There is no aircraft, radio, PX4 API or external telemetry integration. Model-service processing was used for authorship, while the delivered application runs locally.

No human participants were recruited or observed. Whether grouping reduces search effort, whether prominent ownership improves understanding, and whether chronological order helps reconstruct incidents remain hypotheses. The tests support semantic correctness and described interaction paths only. The accessibility review has the gaps recorded in [accessibility-findings.md](accessibility-findings.md), including no assistive-technology user session and no complete WCAG conformance audit.

The next reviewable step is to open the interrupted incident at seconds 3, 4, 5 and 7 and compare all three views. A future participant study would first need the unresolved consent, review, recruitment, sample-size and accommodation decisions in [participant-protocol.md](participant-protocol.md), plus an accessible unscored practice example. Those activities have not been performed or authorized by this delivery.
