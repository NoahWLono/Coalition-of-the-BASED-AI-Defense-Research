# Portfolio publication verification

Recorded 17 October 2026 for the first portfolio import and dark-mode update. Checks were performed by AI assistants on the local workstation. They establish the results described below, without human usability or operational validation.

## Publication boundary

The originating chats for ground control, medical dispatch and Prozorro had final completed handoffs before their project directories were edited or copied. Geolocation had already been completed and published in this repository. The autopilot and CEDAR chats were still active at the packaging checkpoint; their source was excluded.

The original geolocation commit remains in Git history. Its files now live under `project04-geolocation-lab/`. Every imported project is a regular directory with its own README, source and evidence; nested Git histories and local environments are excluded.

## Checks on the publication checkout

| Project | Commands and observed results |
|---|---|
| Geolocation | `python3 -m unittest discover -s tests -v`: 32 passed. Both browser scripts passed `node --check`. Theme adapter checks covered dark default, saved reload, live System updates, explicit preference, invalid saved values and blocked storage. |
| Ground control | `npm test`: 31 passed. `npm run evaluate`: 1,749 model/render records across ten scenarios and 53 checkpoints, zero mismatches. `node tools/contrast-check.mjs`: 44 selected CSS-token pairs passed across both themes. |
| Medical dispatch | `python -m pytest -q`: 138 passed and 48 scenario subtests passed, using the existing pinned Python 3.12 environment. `python -m dispatch.audit results`: 74 schedules and 17 tiny agreements valid. `python3 scripts/build_viewer.py --check`: generated HTML matches all four evidence sources and its template. |
| Prozorro | `bash scripts/reproduce.sh`: 56 tests passed, report regeneration, rational arithmetic reconciliation and artifact validation passed. The retained dataset has 50 unique real lots and zero real leads; the distinct synthetic exercise has one expected synthetic lead. |

Before copying, the medical project also completed a fresh bounded experiment and audit. Its time-limited two-charger incumbent varied, as documented in that project's verification report. The original saved scientific results were preserved. Prozorro's separate theme verification rebuilt its outputs twice with socket access blocked; all 14 real and four synthetic files matched.

An independent assistant checked the three existing interface theme scripts, relevant HTTP routes, portable artifact links, and the ground-control and Prozorro manifests. Its finding about geolocation's outdated hashes was corrected by refreshing the manifest after the final theme edits. Project hashes were checked again after publication metadata cleanup.

## Browser observations

The coordinator used the in-app browser against loopback servers. All four primary pages were inspected in dark mode. Light selection, persistence after reload, System selection, and return to Dark worked on each. The operating system was dark during those rendered checks. Live operating-system changes and storage-denial branches were exercised with browser-API adapters, rather than by changing the workstation settings.

The geolocation map uses theme tokens for grid lines, landmark labels, camera markers and cover regions. Dark boundary opacity is 0.42; light boundary opacity remains 0.22. Solver inputs and results are unchanged. Ground control rendered the interrupted-handover checkpoint and switched among its three interface designs. The medical viewer switched to the online baseline and displayed the saved rolling-MILP objective of 1,793 and five on-time deliveries. Prozorro's real report retained its unvalidated-screening notice and zero real leads.

The ground-control minimal page and Prozorro synthetic report also opened in dark mode. At the observed narrow viewport of 302 CSS pixels, each primary project page had document scroll width equal to viewport width. Tables can scroll within their labelled regions. No console errors were returned for the inspected pages. These checks are a focused browser smoke test; the original full ground-control browser matrices and screenshots still describe its earlier light-theme delivery.

Dark-mode previews:

- [Geolocation laboratory](previews/geolocation-dark.png)
- [Ground-control laboratory](previews/ground-control-dark.png)
- [Medical dispatch comparison](previews/medical-dark.png)
- [Prozorro comparability audit](previews/prozorro-dark.png)

## Packaging

Project manifests cover the published files and are evaluated from each project's directory. Browser downloads, virtual environments, caches, bytecode, nested Git metadata and duplicate archives are excluded. Limited filename/content scans checked for credential files and private-key markers; this was not an exhaustive security audit.

Recorded home-directory paths and machine hostnames were replaced with publication placeholders in historical logs and environment metadata. Versions, test outcomes and numerical results were retained. Medical HTML was regenerated after metadata redaction so its embedded source hashes describe the published evidence. Third-party data/source attribution remains in each project's documentation; the portfolio adds no blanket license.

## Final two projects, 18 October 2026 UTC

The Autopilot and CEDAR originating chats subsequently delivered final completed handoffs and became idle. Their source was inspected and modified only after that completion check. This second import completes the six-project portfolio. The earlier exclusion above records the first import's boundary.

### CEDAR

The application, portfolio page, 18 generated documentation pages and current decision-report templates now offer Dark, Light and System. The saved preference is read before paint; invalid values and blocked storage are handled safely. Decision reports allow the exact theme controller through a CSP hash while retaining escaped source excerpts and the prohibition on external resources.

The publication checkout passed all 59 tests, including a regression check for that CSP allowance. The completed project had 58 tests before the appearance update. A fresh evaluation of the themed source produced 2,952 comparisons with zero mismatches and 601 baseline assertions/citations. Five retained top-level decision ZIPs passed their package verifiers and decision reproduction checks.

The four API decision packages were regenerated from their original decision envelopes. The decision JSON, evidence CSV, source members, timestamps, review digests and stale outcomes are unchanged. Only the report appearance, included verifier and corresponding file manifests changed. Original API packages and their old delivery manifest remain under `artifacts/history/light-appearance/`. The original recording, screenshots, PDFs and browser decision ZIP remain byte-identical. The current delivery manifest covers 263 publishable files; its own bytes are excluded from its inventory.

The coordinator checked all seven application views in the browser, selected Light, reloaded to confirm persistence, selected System, and returned to Dark. The portfolio page and standalone sample report also switched correctly; the sample report retained its selection after reload. The narrow application page had no document overflow. The inspected application and report returned no console errors. These focused appearance checks supplement the original functional browser evidence; they do not repeat its entire workflow or clean-environment run.

### Autopilot failsafe laboratory

The saved-results viewer provides a theme selector, an accessible run ledger, latency comparisons, release/outcome/search filters and links to the retained evidence. The original 58-run outcomes remain 55 PASS, two expected disabled-failsafe FAIL and one text-assertion FAIL. Four affected traces separately pass the corpus 1.0.1 retrospective replay. No fresh full simulator run of corpus 1.0.1 is claimed.

The appearance update passed 41 unit tests, 17 theme behavior assertions and 18 selected foreground/background contrast pairs at a ratio of at least 4.5. The original saved results were independently re-evaluated without writes before the publication transformation; all 58 outcomes matched, four corrected replays passed, both deliberately wrong-mode replays were detected, and all 522 provenance/isolation checks passed. Nine independent-reader DataFlash inspections remain part of the historical evidence.

In the browser, Light persisted after reload, System resolved to the workstation's dark setting, and Dark restored the intended palette. The text-assertion filter showed one run, the expected-control filter showed two, the release filter showed 29, and an unmatched search showed the explicit empty state. Reset restored all 58 runs. The narrow viewport had no document overflow, and no console errors were returned.

Publication inspection found host identifiers in binary telemetry as well as text metadata. The [redaction record](../project01-autopilot-failsafe/docs/publication-redaction.md) and [machine report](../project01-autopilot-failsafe/evidence/publication-redaction.json) describe the derivative files, permitted field changes, original commitments, refreshed seals and before/after comparisons. The private originals remain separate and unchanged. These public copies must not be described as byte-identical original telemetry.

The completed derivative check compared 1,953,877 MAVLink frames and 9,742,255 decoded DataFlash records. Only 193 telemetry messages required permitted identity-field replacements. All 58 full evaluator result dictionaries remained equal; four corrected replays passed, both wrong-mode controls remained accepted, and a fresh audit passed all 522 checks. All 66 derivative seals verified their original 1,422-member lists, and 45 trace-input hash references resolved. The redaction report records 346 changed-file hash commitments. All 1,669 private original files remained unchanged. Seven synthetic redactor regression tests passed, including the truncated identifier field.

Future runs use a fictional namespace hostname and a synthetic `/etc/machine-id` overlay. A namespace smoke check verified those values, a separate network namespace, loopback-only interfaces and an empty routing table. The original isolation flags, read-only host filesystem, per-case timeout and writable-project boundary remain in place. This smoke check did not execute SITL.

### Final packaging

The import retains the Autopilot telemetry/DataFlash evidence, pinned source excerpts and GPL license, and CEDAR's recording, PDFs, screenshots, decision exports, source fixtures and attribution. Downloaded firmware executables, dependency runtimes, virtual environments, caches, runtime databases and duplicate whole-project archives are excluded. Historical diagnostic text and upstream snapshots are preserved rather than reformatted. PDFs are marked binary in Git.

Additional dark-mode previews:

- [Autopilot saved experiment](previews/autopilot-dark.png)
- [CEDAR procurement workbench](previews/cedar-dark.png)

## Portfolio numbering

The user's final naming request assigns projects 1–6 in the main README order: Autopilot, ground control, medical dispatch, geolocation, Prozorro and CEDAR. Folder prefixes are `project01` through `project06` so ordinary filename sorting matches that order. Current README titles, launch paths, interface labels, portable links and affected file manifests use the new numbering.

Historical task requests, experiment seeds, captured command output, source acquisition records and archived delivery packages keep their recorded identifiers. Renumbering those records would alter their provenance. The main README maps the old task numbers to the current portfolio numbers.

Checks after renaming passed: 31 ground-control tests plus its 1,749-record evaluation; 138 medical tests and 48 subtests plus the schedule audit and exact viewer check; 32 geolocation tests; and the 56-test Prozorro reproduction with report/hash validation. CEDAR's 28 focused release/export tests passed after its rename, following the 59-test appearance check above. The Autopilot viewer regenerated and passed its exact check from the new project folder. Browser inspections confirmed the updated project labels and dark appearance.
