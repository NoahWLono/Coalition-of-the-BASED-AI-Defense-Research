# Appearance update and historical evidence

The portfolio publication adds a Dark, Light and System selector to the local application, portfolio entry page, generated HTML documentation and current sample decision reports. Dark is the default. A stored preference is read before styles paint; System follows operating-system changes while the page is open. Blocked browser storage falls back to an in-memory preference.

The theme changes presentation only. All seven application views, source excerpts, evidence dialogs, tables and status badges use the selected palette. Decision reports permit only the exact appearance controller through a SHA-256 Content Security Policy hash. Supplier content remains escaped text, and the report cannot load external scripts or contact a service.

## Preserved evidence

The screenshots, PDFs, `artifacts/cedar-demo.webm`, `artifacts/browser-decision.zip` and original browser/test/clean-reproduction logs retain the original light appearance. Those records describe the version tested when they were created. They do not establish browser or clean-environment validation of this appearance update.

Original API-replay packages are retained under `artifacts/history/light-appearance/`. The checksums in `artifacts/walkthrough.json` and `artifacts/milestone-a.json` refer to these original packages. The prior `DELIVERY_MANIFEST.json` is also kept there as a historical inventory of the original delivery paths.

The current `full-decision.zip`, `full-stale-decision.zip`, `slice-decision.zip` and `slice-stale-decision.zip` are rebuilt from the original decision envelopes. Only `report.html`, the included verifier source and their file-manifest entries change. `decision.json`, `evidence.csv` and every source member remain byte-identical. Original timestamps, record digests, review history, approved/conditional decisions and stale outcomes remain recorded exactly as before.

## Publication metadata redaction

Three historical diagnostic logs (`artifacts/api-red.txt`, `artifacts/state-red.txt` and `artifacts/initial-red.txt`) replace seven occurrences of the original local home-directory prefix with `<HOME>`. This changes filesystem metadata only. Error text, test observations and all other bytes in those logs are retained. The private originals are unchanged. Decision ZIPs, PDFs, video and screenshots are unchanged by this metadata cleanup.

## Reproduce the appearance outputs

Run from the `project06-cedar` repository folder:

```sh
uv run --frozen python scripts/refresh_report_themes.py
uv run --frozen python scripts/build_portfolio.py --html-only
uv run --frozen python -m pytest -q
uv run --frozen python scripts/verify_package.py artifacts/full-decision.zip
uv run --frozen python scripts/reproduce_decision.py artifacts/full-decision.zip
uv run --frozen python scripts/write_delivery_manifest.py
```

The refresh writes `artifacts/theme-package-verification.json`, which records both archive hashes, changed members and the verifier results. HTML generation extracts the verified full package to `artifacts/sample-decision/` so its manifest stays aligned with its report. The `--html-only` option preserves the historical PDFs. The optional complete-source ZIP can be built locally with `scripts/release.py`; the public repository does not include a duplicate `dist/` archive.

The current delivery manifest inventories publishable files and their current hashes. It excludes itself, duplicate source archives, runtime databases, virtual environments, caches and Git metadata. Its functional-tree fingerprint identifies the appearance update; the older clean-reproduction fingerprint remains a historical measurement.

Hash checks establish internal consistency. They do not authenticate suppliers or reviewers, establish claim truth, or approve a current workspace from an older exported decision.
