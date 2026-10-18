# Ground-control interface laboratory contract

All vehicles, observations, actors, locations and incidents are synthetic. Time is integer seconds from replay start. The engine uses no randomness and no wall-clock timestamps for decisions. Script order breaks ties between simultaneous events. Browser playback advances one simulated second per wall second; pause and navigation stop the timer. The app serves only on loopback and uses no external services.

## Data

`data/scenarios.json` is an array of ten objects: `id`, `title`, `vehicle`, `location`, `description`, `duration`, `completionCondition`, `events`, `checkpoints` (array of integer seconds). Events have `at` and `type`; array position is their stable sequence number. Events must be in nondecreasing time order. Initial state before any event is unknown for observations and ownership; handover is idle and target is none. Completion is incomplete until a valid complete event.

Event types and fields:

- `observe`: `field` is principal, mode, or telemetry; `value` is a string; optional `ttl` in seconds. Defaults: principal no expiry, mode 10, telemetry 5. Evidence is known when age <= ttl and stale when age > ttl. null value means unknown.
- `owner`: `actor`, optional `ttl` (default 30). Only establishes initial ownership in idle state; later ownership changes require the handshake or reconciliation.
- `alarm`: `id`, `label`, `group`, `severity` (critical, warning, advisory). A group is a fictional issue identifier, not an inferred causal claim.
- `clear`: `id`. Removes an active alarm. Log history remains available.
- `ack`: `id`, `actor`. Records receipt for an active alarm; multiple actors remain visible. Has no ownership effect.
- `request`: `id`, `from`, `to`, `deadline` (absolute replay second). Valid from idle, completed, cancelled or timed-out, with known current owner matching from, a distinct nonempty target, and a future deadline.
- `accept`: `id`, `actor`. Valid only for the requested id and target before deadline. Handover becomes accepted and owner becomes unknown pending confirmation. Next actor is Supervisor.
- `confirm`: `id`, `actor`. Valid only for accepted id and actor Supervisor before deadline. Owner becomes the target, phase completed, target none.
- `cancel`: `id`, `actor`. Valid only in requested phase by source or Supervisor. Keeps source ownership; phase cancelled and target none.
- `interrupt`: `id`. Valid in requested or accepted phase. Phase interrupted and owner unknown, target retained, Supervisor must reconcile.
- `conflict`: `reports` (array of strings). Ownership becomes unknown, phase conflicted, Supervisor must reconcile. Reports remain in log.
- `reconcile`: `actor` must be Supervisor, `owner` nonempty. Valid in interrupted, conflicted or timed-out phase. Establishes owner; phase completed and target none.
- `complete`: valid only when no active alarms, known owner, and phase idle, completed or cancelled. Marks completion complete. Scenario author must also clear principal using an observation such as No active issue.

At a pending deadline, timeout occurs before events at that timestamp. Requested timeout retains source ownership; accepted timeout leaves ownership unknown. Phase becomes timed-out, target remains for diagnosis, and next actor is Supervisor. Invalid events are recorded as rejected and have no effect. Acknowledgment cannot imply acceptance or ownership. Repeated or delayed acceptance after a terminal phase is rejected. An owner observation cannot bypass recovery.

## Engine API and facts

`src/engine.mjs` exports `replay(scenario, second)`, `facts(state)`, and `ReplayController(scenario)` with `seek(second)`, `reset()`, `step(delta=1)`, `play()`, `pause()`, and `tick()`; `tick` advances only while playing. Seek/reset always pause. State includes `time`, `observations`, `owner`, `handover`, `alarms`, `history`, `rejected`, `completed`. Every fact is `{value, status, at}`; status is known, stale or unknown; unknown timestamps are null. `facts` returns an object keyed by:

| Key | Meaning and string value |
| --- | --- |
| principal | Observation of principal issue |
| mode | Observation of control mode, separate from owner |
| owner | Current actor, or Unresolved |
| handover | Phase string |
| target | Target actor, or None |
| nextActor | Target for requested; Supervisor for accepted/interrupted/conflicted/timed-out; otherwise current owner |
| telemetry | Most recent telemetry observation |
| lastReliable | Most recent non-null telemetry value, retained as historical evidence |
| acknowledgments | Active alarm receipts sorted by alarm id then actor, e.g. a1: Operator A; None when empty |
| alarmGroups | Active alarm id/group mappings sorted by id, e.g. a1: link; a2: link; None when empty |
| completion | incomplete or complete |

Observation timestamps are event times. lastReliable is always known historical evidence at its original time, or unknown if absent; it is never presented as current telemetry. Other derived facts retain their last change/evidence timestamp. Alarm receipt and grouping timestamps are most recent receipt and alarm-change timestamps respectively. Initial empty receipts/groups/phase/target/completion are known at 0.

`data/oracle.json` contains an array of `{scenarioId, at, rationale, expected}`. Expected maps every fact key to literal `{value,status,at}` records. It is authored from incident narratives and the declared rules without importing the replay engine, view renderer, or evaluator. Assistant authorship is declared; this is a separate specification oracle, not human validation.

## Presentation and evaluation

All views use the same `replay` output. `src/views.mjs` exports `renderView(state, variant)` returning escaped HTML. Variants are chronological, grouped and handover. Every fact renders exactly once with `data-fact`, `data-value`, `data-status`, `data-at`, visible value text and timestamp/state text. Hidden facts sit inside native `details`. Chronological buries principal, groups, next actor and historical telemetry in one evidence disclosure; grouped puts handover details in one disclosure; handover puts detailed alarms/receipts in one disclosure. No fact is intentionally omitted. `data-visibility` records visible or obscured. The browser evaluator verifies actual DOM text, visibility and metadata against the oracle. The independent evaluator compares exact value, state and timestamp and catches absence, stale promotion, wrong owner and wrong grouping. Step counts describe disclosure activations from a defined initial screen, not human completion times.

## Implementation decisions

Use native HTML, CSS and ES modules, Node built-in tests and HTTP server. No runtime dependencies, build system, external fonts or analytics. A dedicated directory isolates work because the parent repository has no commits and unrelated untracked projects. The interface uses a pale blue-gray work surface, dark navy text, indigo focus, red critical and amber caution labels, with words and shapes preserving meaning in grayscale. Native buttons, selects and disclosures provide predictable keyboard access. The initial selected scenario is an interrupted handover.
