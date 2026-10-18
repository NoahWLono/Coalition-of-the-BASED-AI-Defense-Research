# Initial local execution record

This record describes the initial implementation before the user's subsequent request to publish the project on GitHub.

Executed locally on 2026-10-17 in America/Toronto. The implementation lives in a new dedicated project directory. The parent repository initially had no commits on `codex/autopilot-failsafe-lab` and contained unrelated projects. No parent files were edited, staged or committed. No remote action was taken.

## Environment and resources

- Host: Momiji, Arch Linux, x86_64, kernel 7.2.11-arch1-1.
- Python: 3.14.8; JavaScript syntax checker: Node v26.12.0.
- Available memory at inspection: about 14 GiB total, 7.6 GiB available. Workloads ran in one Python process each without a GPU.
- Optional figure rasterizer: rsvg-convert 2.63.3, Cairo 1.18.6. The interactive app needs only Python and a browser.
- Seed: 240017. Angular pad: 1e-8 degrees. Solver lattice: 128 by 128 for the benchmark; independent reference: 256 by 256. Supplementary teaching audit: 256 by 256.
- No project dependencies were downloaded or installed. No private data, imagery or location service was used. The code executes locally; the coding assistant uses model-service processing.

## Executed commands

Commands below were run from the project directory in Bash. The Python commands also work unchanged in Fish. The shell script explicitly requires Bash.

```sh
python3 -m geolab.generate --analytic-only
python3 -m geolab.generate
python3 -m unittest discover -s tests -p test_reference.py -v
python3 -m unittest discover -s tests -p test_solver.py -v
python3 -m unittest discover -s tests -p test_evaluation.py -v
python3 -m unittest discover -s tests -v
python3 -m geolab.evaluate
python3 -m compileall -q geolab tests
node --check web/app.js
python3 -m geolab.server --port 8764
rsvg-convert reports/teaching.svg -o reports/teaching.png
```

The first solver test run failed because solver.py did not yet exist. Implementation then made those tests pass. Subsequent review added adversarial tests and a regression test for the evaluation failure gate. The saved final suite result is **32 tests, 0 failures**, in `tests.log`. The full refreshed numerical audit took **15.049 seconds**. Its five failure counters are zero: dense-reference exclusions, valid-truth exclusions, inner-point failures, added cells after adding constraints, and non-nested refined cells. Main solver calls total 55.528 ms; main dense reference calls total 13,596.298 ms. These are one-run timings, not throughput guarantees.

Generation was repeated after a review corrected a mislabeled wraparound fixture. The final scene uses camera (-2,-0.95), and the test checks an interval crossing 360 degrees. Other corrections aligned default observation selection, removed a ground-truth coordinate from a scene title, added a Gaussian explanation, and made evaluation exit nonzero on valid-truth exclusions or supplementary reference failures. Final metadata edits added teaching explanations without changing observations or numerical results.

## Independent and review checks

The dense reference uses cross/dot predicates implemented separately from the adaptive solver. Analytic constructions, the separately stored answer keys, and adversarial tests provide distinct checks. All implementations and annotations are assistant-produced; there was no qualified human review. An additional agent reviewed source and checked the reflection derivation with exact rational arithmetic. This review is recorded separately from empirical verification. No formal prover was run, and no floating-point certification is claimed.

The reference checked 51 scenes, containing 428 accepted dense samples; none were excluded. The default inner-point test is vacuous for these narrow scenes, so a supplementary finer audit checks 60 teaching-cell corners and centers. All pass. Additional tests use broad tolerances and rectangular domains to exercise inner cells.

A separate regeneration in a temporary directory compared all 103 generated JSON files byte for byte with the delivered inputs, answer keys and manifest. All matched. The final artifact hashes are stored in SHA256SUMS.

## Browser verification

The local app was opened and exercised in the Codex in-app browser. Observed results:

- Reflection ambiguity I initially has three outer clusters, two with center witnesses. Adding its distinguishing bearing changes the display to one witnessed cluster.
- Increasing resolution from 128 to 256 narrows its resolved area bracket from approximately 0–0.33 m² to 0.01–0.18 m².
- Revealing the camera fetches a separate answer key. Keyboard activation also works.
- The analytic conflicting-bearing scene reports incompatible evidence, an empty cover, and conflicting IDs o1/o2.
- Selecting a Gaussian scene displays the one-sigma assumption and warns that the true camera may be excluded.
- Scene selectors show unique IDs. Desktop DOM width equalled content width at 1020 CSS pixels. A temporary narrow viewport likewise showed no horizontal overflow and was reset afterwards.

An initial browser screenshot was visible during inspection. Later screenshot exports failed with `Unable to capture screenshot`, and two mouse-dispatch attempts timed out. Keyboard activation and DOM checks continued successfully. No complete UI screenshot is claimed as a saved artifact. The standalone teaching SVG was rendered with rsvg-convert and visually inspected as a PNG. This is a generated scientific diagram, not a browser screenshot.

## Source access and remaining limits

Primary-source URLs and access results are recorded in `../docs/geometry.md`. SymPy documentation and Python's HTTP documentation were retrieved. The Blender manual fetch failed; no Blender dependency was introduced. A bundled-dependency discovery call was canceled after it failed to return promptly; the already installed SVG rasterizer supplied the needed visual check.

All requested numerical-prototype deliverables are present. Formal directed-rounding certification, exact continuous topology, real-image evaluation, unknown-orientation inference, and statistical calibration remain outside the delivered evidence. The measured discretization limits and singularity artifacts are retained in the report. No external publication, deployment, contact, spending or remote Git operation occurred.

To rerun the complete workflow, execute `bash reproduce.sh`. To inspect the demonstration, run the local server, choose Reflection ambiguity I, and toggle its calibrated bearing.
