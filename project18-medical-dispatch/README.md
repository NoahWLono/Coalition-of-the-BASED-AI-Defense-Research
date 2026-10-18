# Civilian medical-delivery dispatch simulator

This local research prototype compares dispatch policies for a wholly synthetic civilian supply service. It includes a discrete-event simulator, FCFS and earliest-deadline policies, a bounded time-indexed MILP, an independent schedule checker, and an exhaustive tiny-case reference. No geographic paths, patient data, clinical judgments or real operations are used.

Open the [interactive results viewer](index.html) or start with the [saved experiment report](results/report.md), then the [mathematical model and assumption register](docs/model.md). The [timing contract](docs/contract.md) defines every exported field. The original request is preserved in [mission.txt](docs/mission.txt).

## Saved result

The baseline contains 20 requests, including one cancellation, with three vehicles, four batteries, one charger and two technicians. All policies serve 12 of the 19 eligible requests. The offline MILP reports an integer-slot optimum of 1,663, versus FCFS 2,359 and EDF 2,400. The separate online rolling policy scores 1,793; it has no global optimality claim. The aggregate improvement includes a regional tradeoff, described in the report.

There are 74 checked schedule exports: 39 comparisons, 34 tiny-case witnesses and one capacity-transfer certificate. All 17 tiny instances agree with exhaustive reference minima. The saved full test run passes 138 tests plus 48 scenario subtests. The two-charger solve remains bounded; its own incumbent gap is 36.44%. Reusing the checked baseline schedule gives a better feasible certificate with a remaining 20.32% gap. No operational validation is claimed.

## Results viewer

From the monorepo root:

```bash
cd project18-medical-dispatch
python3 -m http.server 8018 --bind 127.0.0.1
```

Open [the local results viewer](http://127.0.0.1:8018/). You can also open `index.html` directly in a browser. The page uses only local files and works without a network connection. It shows the saved experiment; switching between offline and online views does not run a new simulation.

The viewer starts in dark mode. Its Theme control offers Dark, Light and System; the choice is saved in browser storage when available. System follows operating-system changes while the page is open. Theme colors cover the charts, tables and controls. Original PNGs are available through download links.

The generated page embeds its evidence and SHA-256 source hashes. After changing viewer sources or saved evidence, rebuild it, then check for stale output:

```bash
python3 scripts/build_viewer.py
python3 scripts/build_viewer.py --check
```

The original report and numerical model remain the authority for interpretation. The viewer preserves the two-charger optimization gap, separates offline and online information, and includes regional and category service rates.

## Reproduce

Python 3.12 is the tested interpreter series. Create a virtual environment and install the exact resolved versions:

```bash
cd project18-medical-dispatch
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m dispatch.audit results
```

The `cd` command starts from the monorepo root. When working from a standalone archive, enter the extracted project directory. `uv` can replace pip: `uv pip install --python .venv/bin/python -r requirements-lock.txt`.

Regenerate fixed fixtures and repeat the bounded experiment into a fresh output directory:

```bash
.venv/bin/python -m dispatch.generate
.venv/bin/python -m dispatch.experiment --out rerun-results --offline-limit 3 --online-limit 0.5
.venv/bin/python -m dispatch.audit rerun-results
```

The saved experiment took about 29 seconds on this host. The solver limits bound individual solves; startup, matrix construction, enumeration and plotting add time. The runner makes 12 offline solves, 48 online solves and 17 tiny comparison solves. A three-second offline limit and half-second online limit are defaults, with five seconds for each tiny comparison. There is no background service, paid API or GPU dependency. No software downloads occur during the experiment after dependency installation.

Run one policy and check its schedule independently:

```bash
.venv/bin/python -m dispatch fixtures/baseline.json --policy milp --information offline --time-limit 3 --out single-schedule.json
.venv/bin/python -m dispatch.checker fixtures/baseline.json single-schedule.json
```

For an online solve, set `--information online`; its time limit applies to each decision solve. For a standard-library-only path, `python3 -m dispatch fixtures/hand_four.json --policy fcfs --out hand-fcfs.json` and `python3 -m dispatch.checker fixtures/hand_four.json hand-fcfs.json` need no SciPy or plotting packages. The checker CLI exits zero for valid schedules, one for infeasible schedules and two for malformed input/usage.

Fixtures and heuristic schedules are deterministic. HiGHS chooses among equal-cost MILP solutions; equivalent schedules can differ across solver versions. Time-limited incumbents and bounds can also differ across machines or load. Reproducing the mathematical contract, passing checks and honest bounds matters more than byte-identical timed solutions. Generated figures and reports describe their own saved run; the top-level README describes the original saved run.

## Artifact map

| Location | Contents |
|---|---|
| index.html, viewer/ and scripts/build_viewer.py | Dark-first static evidence viewer, theme controls and reproducible page generator |
| dispatch/generate.py and fixtures/ | Seeded generator, four-request hand case and fixed sensitivity instances |
| dispatch/simulate.py | Heap-based event simulator and two dispatch heuristics |
| dispatch/optimize.py | MILP, solver metadata, fixed-history replay and online policy |
| dispatch/checker.py | Independent standard-library validator, with no scheduling or solver imports |
| dispatch/reference.py and dispatch/tiny_cases.py | Exact rational tiny enumeration and reproducible comparison cases |
| tests/ | Corruption, boundary, exact-agreement, queue and online-information tests |
| results/scenarios/ and results/schedules/ | Exact scenario inputs and JSON/CSV service, charge and rejection exports |
| results/validation/ and results/metrics/ | Per-schedule check records and reconstructed outcomes |
| results/comparison.csv and results/distributions.csv | Aggregate comparisons and region/category outcomes |
| results/figures/ | Comparison, resource timeline, sensitivity and service-distribution PNGs |
| results/tiny_agreement.json | All 17 exhaustive-reference comparisons |
| results/capacity_certificate.json | Stronger feasible certificate for the time-limited two-charger case |
| results/run_metadata.json and results/experiment.log | Actual versions, seed, runnable command, limits, statuses and elapsed time |
| docs/verification.md and docs/commands.txt | Executed verification and command record |
| SHA256SUMS | File-integrity manifest for the delivered package |

The checker verifies feasibility. Exact enumeration checks the tiny optima. Online future-input perturbation tests and source separation check the information boundary. AI code review is documented separately from those methodological checks. No human review or empirical confirmation is claimed.

The next numerical step is to increase the two-charger solve budget while retaining the stronger feasible certificate. Broader seeds, online sensitivity and unexpected disruptions would be separate research extensions. Before real use, aviation, handling and clinical requirements would need to be established outside this prototype.
