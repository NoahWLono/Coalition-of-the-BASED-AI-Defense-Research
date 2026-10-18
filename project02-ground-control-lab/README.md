# Project 2: Ground-control alarm and handover interface laboratory

A local comparison of three interfaces for the same ten fictional civilian inspection incidents. Replay the scripts to inspect alarm groups, stale evidence, control mode, responsibility and handover recovery. The application has no connection to vehicles, radios, flight software or external services.

This is project 2 in the published portfolio. Historical command logs, screenshots, and saved experiment metadata retain the former `project16-ground-control-lab` name and project number; those records have not been rewritten for this renumbering.

## Run

Node.js 22 or later is required. There are no runtime packages to install and no build step. These commands work in Bash or Fish:

```sh
cd project02-ground-control-lab
npm start
```

Open [the local laboratory](http://127.0.0.1:4160). The server listens only on `127.0.0.1`. Stop it with Ctrl+C. To choose another port, use `env PORT=4161 npm start`.

The Theme control at the top of the page offers Dark, Light and System. New visits start in Dark. Your choice is saved in this browser; System follows changes to the operating system's color preference. If browser storage is unavailable, switching still works for the current page. The same control is available in `minimal.html`. Alarm severity, freshness words and symbols, and the grayscale check work in either color scheme.

Select an incident and an oracle checkpoint, then switch among Chronological alarms, Incident groups and Handover state. Switching design preserves replay time. Play advances one simulated second per second; pause, timeline seeking, step, rewind and reset operate only on the scripted replay. Evidence disclosures are keyboard accessible. Changing incidents closes disclosures and resets time. The four export buttons download scenario JSON, current-state JSON, current-trace JSON and the generated correctness matrix.

Start with the interrupted handover at seconds 3, 4, 5 and 7. Operator B's receipt at second 3 leaves Operator A responsible. Acceptance at second 4 makes ownership unresolved. Interruption at second 5 requires Supervisor action. Reconciliation at second 7 restores Operator A.

## Verify

```sh
npm test
npm run evaluate
node tools/contrast-check.mjs
npm run test:browser
```

`npm test`, `npm run evaluate` and the contrast check use only Node built-ins. The browser command uses Playwright 1.62.1 and a project-scoped Chromium installation. It starts and closes an ephemeral loopback server, runs one headless browser, and saves matrices, inspection results and screenshots. It does not require the server from `npm start`.

On a different machine, install the pinned verification dependency and its browser. The app itself does not need these downloads:

```sh
npm install --no-save --package-lock=false playwright@1.62.1
env PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" npx playwright install chromium --only-shell
npm run test:browser
```

Browser tooling on this Arch host used Playwright's Ubuntu 24.04 fallback build successfully. The helper first looks for a local Playwright package, then the Codex bundled runtime; `PLAYWRIGHT_MODULE` can override the module path. Browser downloads remain in `.cache/`, which is excluded from version control. No system packages or daemons were installed.

Regenerate the matrix after changing scripts or presentation code. The CSV export downloads `evidence/correctness-matrix.csv`, the last generated result; it is not recalculated during playback. JSON exports capture the selected script and current replay position.

The theme update passed all 31 Node tests and the 1,749-record model/render evaluation. The five theme tests cover startup preference, persistence, system changes and unavailable browser storage through bounded browser-API adapters; they do not render a browser. The contrast check reads current CSS tokens and checks 44 selected pairs across both themes. See [theme unit-test results](evidence/theme-unit-tests.txt), [evaluation log](evidence/theme-evaluate-log.txt) and [contrast results](evidence/contrast.json). The saved browser reports and screenshots below record the original light-theme delivery; they have not been regenerated for this theme update.

## Review the artifacts

- [Comparison and verification report](docs/comparison-report.md), including the concrete differences and limits of the three views.
- [Accessibility findings](docs/accessibility-findings.md), with executed checks and remaining user-validation gaps.
- [State machine](docs/state-machine.md) and [data contract](docs/contract.md).
- [Ten incident scripts](data/scenarios.json), [literal checkpoint oracle](data/oracle.json) and [scenario narratives](docs/scenario-catalog.md).
- [Generated correctness matrix](evidence/correctness-matrix.csv) and [actual browser matrix](evidence/browser-correctness-matrix.csv).
- [Model/render evaluation](evidence/evaluation.json), [browser results](evidence/browser-report.json), [DOM mutation regressions](evidence/audit-regressions.json), [unit-test log](evidence/unit-tests.txt) and [review disposition](evidence/review.md).
- [Chronological screenshot](screenshots/chronological.png), [grouped screenshot](screenshots/grouped.png), [handover screenshot](screenshots/handover.png), [alarm burst](screenshots/alarm-flood.png), [grayscale](screenshots/grayscale.png) and [390-pixel layout](screenshots/mobile.png).
- [Optional participant protocol](docs/participant-protocol.md) and [unused task materials](docs/task-materials.md).
- [Sources](docs/sources.md), [host and version record](evidence/environment.json), [executed-command record](evidence/commands.txt) and [file hashes](evidence/SHA256SUMS).

The oracle was authored by a separate assistant from the narratives and declared rules without reading the engine or UI. It supplies a separate specification check, not human validation. All fixture values are synthetic. There were no participants and no measurements of workload, task completion time, usability benefit or operational safety. The model's ownership protocol and freshness thresholds are laboratory assumptions. AI-assisted authoring used model services, so this is not an offline AI workflow.
