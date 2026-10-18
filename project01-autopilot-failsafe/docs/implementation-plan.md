# Autopilot failsafe laboratory implementation plan

**Goal:** Execute twelve documented fault scenarios on two pinned compatible SITL releases, with independent evaluation and bounded conclusions.

**Architecture:** A Python MAVLink controller drives a fresh simulator for each JSON scenario inside an isolated namespace. A separate offline evaluator checks raw evidence, while an independent DataFlash reader cross-checks selected traces.

**Tech stack:** Official static ArduCopter SITL binaries, Python 3.12, pymavlink 2.4.49, Bubblewrap and standard Linux tools.

**Spec:** `docs/design.md` and the user-supplied project specification.

## Global constraints

- Local software simulation only; no publishing, remote writes, real devices or paid services.
- Preserve twelve cases and the two-release requirement even when a gate fails.
- No sudo or host networking changes; fail closed if namespaces are unavailable.
- One process at a time, speedup 4, bounded per-case timeout and memory.
- Store raw logs, exact configs, timings, commands, source versions and results.

## Review focus

- Unconfirmed faults cannot yield a pass.
- Baseline and starting conditions must be checked before injection.
- Observation gaps and stale timestamps cannot silently satisfy deadlines.
- Recovery and compounds must preserve required ordering and sustained modes.
- Timeout, interruption and evaluator error must preserve evidence and kill children.

## Tasks

- [x] Inspect host and source documentation; select and hash both releases.
- [x] Write starter transition table and isolation design before runner.
- [x] Define JSON scenario and trace contracts; write evaluator tests with synthetic labels.
- [x] Implement runner and cleanup; execute baseline then three complete starter cases on 4.5.6.
- [x] Expand and execute the twelve-case corpus on both releases, schedules and negative controls.
- [x] Independently inspect three DataFlash traces and audit socket/process cleanup.
- [x] Review code and evidence; write comparison, demonstration and one-command reproduction; run final gates.
