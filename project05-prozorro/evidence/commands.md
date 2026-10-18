# Executed commands and decisions

All commands ran locally from the project directory unless the full path indicated otherwise. Bash was explicitly used for multiline shell commands. The original repository was unborn on `codex/autopilot-failsafe-lab`, with unrelated untracked `project11-autopilot-failsafe/`. Project31 was isolated in its own directory; no repository branch, commit, remote or unrelated file was changed.

The host inspection ran `uname -a`, `free -m`, `python --version`, `command -v python3 uv curl git node pdftotext`, `git status --short --branch` and applicable AGENTS.md searches. The version snapshot is in environment.json. No dependencies were installed.

Initial read-only probes used Python urllib to inspect the public API, one ordinary paper record and feed behavior. A 1000-entry identifier feed confirmed unsupported title fields were silently omitted; broad feed scanning was abandoned. No feed contents were retained. Official source-document retrieval and browser discovery are described in docs/source-research.md and its ledger.

Implementation and regression commands:

```sh
env PYTHONPATH=src python -m unittest discover -s tests -p test_acquire.py -v
env PYTHONPATH=src python -m unittest discover -s tests -p test_adapter.py -v
env PYTHONPATH=src python -m unittest discover -s tests -p test_report.py -v
env PYTHONPATH=src python -m unittest discover -s tests -v
```

The retained `*-red.txt` and `*-green.txt` files contain the observed failing and passing runs. Core tests were first run by the bounded core worker before its implementation. A thousand-pack precision regression caught default Decimal-context rounding and was corrected. Final review regressions cover package bounds, cross-lot links, unavailable contract state, VAT contradictions, publication dates and reviewed-report text. A temporary failure during the package-parser correction was traced to the `4` in `A4` being treated as part of a spaced number; a word-boundary rule corrected it.

Acquisition ran the same acquire function from Python before the CLI was added. The request caps for its three invocations were 150, 68 and 42. Actual requests were 82, 26 and 17, for a total of 125. Existing extracts and previously excluded candidate IDs were skipped. No request was retried after an access denial; all instrumented procurement responses were HTTP 200.

```sh
env PYTHONPATH=src python -m prozorro_compare report
env PYTHONPATH=src python -m prozorro_compare demo
python scripts/reconcile.py
bash scripts/reproduce.sh
```

An independent arithmetic mutation check changed the expected numerator from 669 to 670 in a temporary normalized file; the checker returned exit 1. The temporary mutation was not retained. Reconciliation evidence records the real baseline. Repeated report builds were checked byte-for-byte in temporary directories.

For HTML QA, `python -m http.server 8765 --bind 127.0.0.1 --directory output/real` served only the report locally. The in-app browser failed to attach a webview; no screenshot or visual-browser verification is claimed. HTML escaping and deterministic content tests passed. The temporary server was stopped.

The local copyediting detector was run on README, contract, plan, source research and audit prose. Its findings and dispositions are in copyedit-report.txt. No memory files were modified.
