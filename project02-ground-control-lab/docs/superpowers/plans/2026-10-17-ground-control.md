# Ground-control laboratory implementation plan

**Goal:** Deliver ten deterministic fictional incidents, three purposeful views, independent fact checks and reviewable evidence.

**Architecture:** A pure event reducer exposes timestamped facts. Literal checkpoint truth tables are authored separately from it. All renderers consume the same state; browser checks compare rendered facts with those tables.

**Tech stack:** Native ES modules, HTML/CSS, Node built-ins; available local Chromium automation for verification.

**Spec:** The supplied mission, preserved in `docs/mission.txt`, and `docs/contract.md`.

## Constraints and review focus

Local loopback only; synthetic data only; no remote publication; no new paid services; bounded single-browser verification. Keep acknowledgments separate from ownership. Review timeout ties, stale current ownership, delayed acknowledgments, replay reset races, and hidden facts after view changes.

## Tasks

- [x] Write first interrupted-handover fixture and literal oracle; assert ownership is unresolved after acceptance and interruption, then reconciled only by Supervisor.
- [x] Run failing model tests, implement `replay`, `facts` and `ReplayController` in `src/engine.mjs`, and verify a minimal replay page before adding variants.
- [x] Author ten scripts and literal oracle tables in `data/`, independently of reducer and renderer implementation.
- [x] Implement `renderView(state, variant)` plus selectable controls, pause, reset, rewind, checkpoint navigation and JSON/CSV downloads. Preserve focus during ticks.
- [x] Implement exact fact comparison and CSV matrix generation. Seed wrong ownership, stale promotion and wrong alarm-group mutations and require failures.
- [x] Run all checkpoints in the real browser across three variants. Exercise keyboard-only tasks, grayscale, reduced motion, narrow viewport, reset during playback and exports. Save screenshots and results.
- [x] Review implementation, fix concrete defects, and write comparison, accessibility, source/provenance and optional participant materials with no human-performance claims.

No remote push or deployment. No commit of unrelated files. Record actual commands and outcomes in evidence.
