# Verification evidence

The user-required sequence was followed: the two-vehicle four-request fixture and its witness were written first, then the independent checker, then the optimizer. The checker has no solver or simulator imports. Before implementation, its hand-fixture test failed because the checker was not implemented; the optimizer test initially failed because its module did not exist.

The final full suite passes 138 tests plus 48 scenario subtests. Coverage includes no requests, simultaneous deadlines, no feasible vehicle, no batteries, no technicians, no chargers, charging bottlenecks, cancelled requests and return beyond the horizon. Deliberate corruptions exercise duplicated service, missing records, resource overlaps, forged timings, invalid IDs and battery reuse without recharge.

All 17 exported tiny cases agree between the MILP objective/bound and the independent exact rational enumerator. The four-request optimum is 2 by an analytical energy-count lower bound and a matching schedule. Enumeration visits 573 memoized states and 1,270 transitions for that case. Enumeration is bounded by explicit input/state guards; no general theorem or formal-prover result is claimed.

All 74 exported schedules pass a fresh artifact audit. That count comprises 39 policy comparisons, 34 tiny witnesses and one capacity-transfer certificate. The audit reopens JSON, calls the independent checker and recomputes metrics. It also verifies recorded online visibility and executed-operation logs. Source separation and future-demand perturbation tests provide the additional online-information checks; replay logs alone would not establish causality.

An AI reviewer independently recomputed objectives from all 73 schedules present before the transfer certificate was added, without importing the metrics or solver code, and found agreement. This is a separate calculation on synthetic inputs. The transfer witness was then checked by the same independent schedule checker and the artifact audit. All code, labels and review in this session were assistant-produced.

Review found and resolved four material issues:

- A supplied fixed prefix could have its battery and technician identities changed. The failing regression reproduced B2/T2 becoming B1/T1. Materialization now preserves supplied historical resource identities and validates the prefix.
- Input validation accepted numeric IDs, a missing category and an incomplete matrix. Four failing regressions now pass after boundary validation was added.
- The sensitivity plot did not mark a time-limited MILP incumbent. It now marks that row, and the report retains its objective, lower bound and gap.
- Run metadata omitted the interpreter and module invocation. It now records a correctly quoted command, an argument array and the working directory.

The two-charger solve is the only non-optimal offline comparison in this saved run. Its raw incumbent objective is 2,085, its lower bound is 1,325.1552 and its translated gap is 36.44%. A separately checked transfer of the one-charger schedule improves the known feasible upper bound to 1,663, reducing the remaining gap to 20.32%. The raw solver result remains available. The online policy records 47 optimal local solves and one limited local solve, with no fallback; these statuses do not imply global online optimality.

The four generated PNGs were visually inspected for legibility and data alignment. The final sensitivity image explicitly identifies the limited solve. No external publication, real-system operation or spending occurred. The original experiment process took 28.83 seconds; later report/plot corrections and certificate validation are separately noted in run_metadata.json.

Final reproducible checks:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m dispatch.audit results
.venv/bin/python -m dispatch.checker fixtures/hand_four.json fixtures/hand_four_schedule.json
sha256sum -c SHA256SUMS
```

The mathematical model, fixtures, simulator, heuristics, bounded optimizer, checker, exhaustive reference, exports, figures and reproduction guide are present. No required bounded milestone gate remains blocked. The larger two-charger optimality gap remains open under the explicitly allowed bounded-solution criterion. Operational validation is outside this mission.


## Results viewer verification

The results viewer was added on 2026-10-17 after the bounded research package was complete. It reads the original saved comparisons and group distributions; solver, simulator, model, fixtures and original numerical reports were unchanged. The page generator records SHA-256 hashes of its four CSV/JSON evidence sources. `python3 scripts/build_viewer.py --check` confirms the generated page matches those sources and its template. All 21 local page links resolve, and the embedded evidence contains six baseline policy rows, 36 offline sensitivity rows and 36 baseline group rows. JavaScript syntax was checked with `node --check viewer/viewer.js`.

The existing full suite passed again: 138 tests and 48 scenario subtests. The saved artifact audit again checked 74 schedules and 17 tiny agreements, and the four-request hand witness passed its checker. A fresh bounded reproduction completed in 25.08 seconds outside the release directory, followed by another successful 74-schedule audit. Its two-charger incumbent was 2,571 with lower bound 1,325.1552; time-limited solutions can vary with execution conditions. The original saved result of 2,085 and its capacity-transfer certificate remain intact.

The viewer uses local HTML, CSS and JavaScript. It starts in dark mode, persists Dark/Light/System when browser storage is available, applies a saved preference before the stylesheet paints, and follows live system changes when System is selected. Original PNGs are linked for download; the displayed outcome bars and tables use theme colors. Browser visual validation is recorded separately by the monorepo release task.
