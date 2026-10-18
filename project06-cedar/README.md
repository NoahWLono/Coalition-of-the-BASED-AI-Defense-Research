# Project 6: CEDAR procurement evidence workbench

**A local procurement and assurance workbench for a fictional six-aircraft civilian inspection fleet.**

CEDAR connects purchasing requirements to versioned supplier evidence, exposes unresolved cost and software questions, and preserves review decisions when the evidence changes. It is a synthetic portfolio demonstration directed by Noah Weinberger and implemented with AI assistance. No customer validation, field capability, contractor relationship or professional endorsement is claimed.

Open [PORTFOLIO.html](PORTFOLIO.html) for the meeting entry point, bilingual PDFs, recording and reviewable decision report. The [completion report](docs/COMPLETION_REPORT.md) records observed results and the remaining pilot scope.

## Open the demonstration

Requirements: Linux/macOS with [uv](https://docs.astral.sh/uv/getting-started/installation/) and Internet access for the initial dependency installation. Python 3.13.15 is pinned; no Node runtime, GPU, paid API, database service or external account is needed. After installation, the demonstration works offline. Windows has not been exercised.

From the portfolio repository root:

```sh
cd project06-cedar
uv sync --frozen
uv run --frozen python -m cedar demo
```

Open [CEDAR on this machine](http://127.0.0.1:8765). The server binds to loopback and uses one worker. The documented commands work in Bash and Fish. Keep the terminal open; Ctrl+C stops the server. The dedicated database is `runtime/cedar.sqlite`. To start a separate pristine demonstration without deleting any prior decisions:

```sh
uv run --frozen python -m cedar demo --db runtime/meeting-02.sqlite
```

The initial corpus and buyer policy are imported automatically into a new database. Existing databases keep their evidence and decisions when the process restarts. Rebuilding source fixtures does not silently replace an existing database. Use a new database path to inspect a regenerated corpus.

The role selector opens a local demonstration sign-in. The accounts are deliberately public:

| Role | Password | Server permissions |
|---|---|---|
| Analyst | `cedar-analyst` | Import inert sources, change assumptions/policy, apply amendments, create snapshots |
| Technical reviewer | `cedar-reviewer` | Accept/reject an assertion interpretation, review a current snapshot |
| Approver | `cedar-approver` | Approve a current technically reviewed snapshot |

These identities demonstrate enforced permission boundaries. They do not establish separate human identities. Do not expose this server to a network or put customer information in it.

## Reproduce the work

```sh
uv run --frozen python -m cedar corpus
uv run --frozen python -m cedar verify
uv run --frozen python -m cedar walkthrough
uv run --frozen python -m cedar export
```

These commands rebuild both synthetic corpora, run the meaningful verification suite and measured evaluation, replay the review/amendment story, and export the sample decision plus complete repository archive. Generated evidence goes to `artifacts/`; repository release archives go to `dist/`. Export does not push, upload, send or deploy anything.

The complete source ZIP includes the recording, PDFs, screenshots and decision packages. Its portable archive format retains the internal `cedar/` folder; after extraction, enter that folder to run the project commands. The public repository folder is `project06-cedar/`. To verify its per-file manifest without installing dependencies:

```sh
python3 scripts/release.py --verify dist/cedar-portfolio-source.zip
```

Optional artifact regeneration uses the pinned development environment:

```sh
uv run --frozen python -m playwright install chromium
uv run --frozen python scripts/browser_check.py --record
uv run --frozen python scripts/build_portfolio.py
uv run --frozen python scripts/clean_reproduce.py
```

The initial Chromium download needs network access; it is only needed to regenerate browser screenshots or the silent recording. PDF/HTML generation is local. Clean reproduction unpacks the already verified source archive into a temporary directory and creates a new virtual environment; it can reuse the host's dependency cache. It does not reset the working application's database.

For the first milestone alone:

```sh
uv run --frozen python scripts/walkthrough.py --scope slice
```

A decision ZIP contains its own standard-library verifier. After unpacking the ZIP into a clean folder, run `python verify.py /path/to/decision-package.zip`. You can also check a package without extracting it:

```sh
uv run --frozen python scripts/verify_package.py artifacts/full-decision.zip
```

Hash checks establish internal consistency relative to the supplied manifest. They do not establish authenticity, genuine reviewer identity, truth of a supplier assertion or current approval after a later amendment. The exporting workspace's current/stale status is recorded at export time.

## What to inspect

- [Product brief and acceptance design](docs/superpowers/specs/2026-10-17-cedar-design.md)
- [Executive brief in English](docs/EXECUTIVE_BRIEF_EN.md) and [French](docs/EXECUTIVE_BRIEF_FR.md)
- [Technical case study](docs/CASE_STUDY.md), [claims ledger](docs/CLAIMS_LEDGER.md), [completion report](docs/COMPLETION_REPORT.md)
- [Four-week pilot proposal](docs/PILOT_PROPOSAL.md) and [interview questions](docs/INTERVIEW.md)
- [Demonstration narration](docs/DEMO_SCRIPT.md), [architecture](docs/ARCHITECTURE.md), [schemas](docs/SCHEMAS.md), [threat model](docs/THREAT_MODEL.md)
- [Research register](docs/RESEARCH_REGISTER.md), [limitations](docs/LIMITATIONS.md), [third-party attribution](docs/THIRD_PARTY.md)
- [Measured evaluation](artifacts/evaluation.json), [API walkthrough](artifacts/walkthrough.json), [separately authored annotations](evaluation/annotation-notes.md)

The application, portfolio entry page, HTML documentation and regenerated decision reports start in Dark mode. The visible Theme selector offers Dark, Light and System, remembers the preference when browser storage is available, and follows operating-system changes while System is selected. The interface remains usable if storage is blocked.

The recording, screenshots, PDFs, browser download and original verification logs preserve the earlier light appearance. The [theme update record](docs/THEME_REFRESH.md) identifies regenerated packages and historical evidence. A complete source ZIP is optional and can be generated locally; it is not duplicated in the public repository.

The implemented browser interface has seven views: overview, requirements, evidence, comparison, software assurance, change review and decision package. Every assessment opens the actual source version. A high score cannot compensate for a mandatory gate. Missing scored evidence spans a score interval, and an unknown required cost remains an open exposure.

## Scope and trust

The full corpus contains six fictional suppliers, twelve packages, forty requirements (18 mandatory, 14 scored, eight informational), 36 base documents in three text layouts, three amendments, two buyer-policy versions and twelve CycloneDX 1.6 inventories. Additional machine-readable files are declared inputs. The answer keys live separately under `evaluation/`; the application never reads them.

The parser is a deterministic baseline for explicit response identifiers in UTF-8 text. It does not perform OCR, read arbitrary PDFs or infer unstated capability. The optional proposal-adapter interface has no live model implementation; model evaluation is unperformed. Synthetic independent-test passages are documentary fixtures. No physical test occurred.

This public portfolio demonstrates local software only. It has no connection to aircraft, operational routing, real infrastructure assessment, legal certification, purchase or vendor contact. INKAS and Marconi were supplied as possible audiences only; the portfolio remains contractor-neutral pending exact legal-entity confirmation.
