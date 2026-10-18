# Geolocation laboratory implementation plan

**Goal:** Deliver the complete bounded synthetic milestone in docs/mission.txt.

**Architecture:** Python standard-library geometry and localhost HTTP service, with an SVG browser interface. A seeded generator writes solver inputs and answer keys separately. A separately implemented point-grid checker audits the adaptive cell solver.

**Spec:** ../../mission.txt

## Decisions

Use a dedicated directory because the parent repository has no commits and contains unrelated work. No installs, paid APIs, network imagery, publishing, or remote Git actions. Coordinates are arbitrary local metres; angles are degrees counterclockwise from positive x. Absolute bearings assume calibrated orientation. Unsigned inter-landmark angles require no orientation and preserve reflection ambiguities. Cells use conservative angular variation bounds, with explicit floating-point limitations.

## Tasks and interfaces

- [x] Generate three analytic fixtures first, then 20 benchmark scenes and held-out extensions. `geolab/generate.py` owns generation; `geolab/reference.py` provides `accepts(scene, point, observation_ids=None)` and `dense_grid(scene, n, observation_ids=None)`. Neither imports solver code. Separate `data/inputs/<id>.json` and `data/truth/<id>.json`.
- [x] Implement and test `geolab/solver.py`: `solve(scene, resolution=128, observation_ids=None)` returns uniform final cells retained by coarse-to-fine pruning, conservative area bounds, center witnesses, component labels, and conflict/unresolved status. Include analytic, wrapping, singularity, monotonicity and boundary tests.
- [x] Implement loopback server and SVG interface. `GET /api/scenes`, `/api/scene?id=...`, `/api/truth?id=...`, `/api/solve?id=...&n=128&obs=o1,o2`; scene and solve never receive truth. Show constraint toggles, uncertainty, multiple components, resolution, and optional truth reveal.
- [x] Run benchmarks with held-out bounded and Gaussian-noise scenes. Measure truth inclusion, dense-reference inclusion, inner-cell soundness, area brackets, runtimes and topology at stated resolution. Write machine-readable report and teaching SVGs.
- [x] Review implementation and browser behavior, fix material defects, record commands/versions and limitations, and deliver reproduction instructions.

## Review focus

Unsigned angles permit disconnected reflected solutions. Bearings must wrap across 360 degrees. A camera coinciding with an observed landmark is undefined. Empty sample grids do not prove conflict. Gaussian intervals are empirical and wrong landmark identities may remain consistent. Coarse components may merge unresolved branches. Zero-width feasible sets can be missed by point sampling but must remain in the cell cover.

## Execution record

The user explicitly authorized implementation choices and continuous execution. Assistant decisions above implement that scope. Agent code review is separate from empirical independence: the dense reference and analytic constructions provide the independent mathematical checks.

All five tasks completed. Evidence: reports/tests.log, reports/evaluation.json, reports/execution.md. Browser screenshot export unavailable; teaching.svg and teaching.png rendered and inspected. Source review findings resolved.
