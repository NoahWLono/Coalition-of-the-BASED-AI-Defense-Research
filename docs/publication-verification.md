# Portfolio publication verification

Recorded 17 October 2026 for the first portfolio import and dark-mode update. Checks were performed by AI assistants on the local workstation. They establish the results described below, without human usability or operational validation.

## Publication boundary

The originating chats for ground control, medical dispatch and Prozorro had final completed handoffs before their project directories were edited or copied. Geolocation had already been completed and published in this repository. The autopilot and CEDAR chats were still active at the packaging checkpoint; their source was excluded.

The original geolocation commit remains in Git history. Its files now live under `project24-geolocation-lab/`. Every imported project is a regular directory with its own README, source and evidence; nested Git histories and local environments are excluded.

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
