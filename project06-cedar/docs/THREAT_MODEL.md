# CEDAR threat model

## Overview

CEDAR is a local synthetic procurement workbench. The supported CLI starts one Uvicorn worker on 127.0.0.1:8765. An operator-selected corpus is copied into SQLite on first use; labelled text becomes a versioned assertion ledger. Deterministic requirement, cost, scoring and software-assurance functions feed the browser and immutable decision records. Public local reads expose synthetic state and source text. The application has no live aircraft, supplier or model-provider connection.

This model incorporates a fresh-context AI source review and locally reproduced regression tests. It is not a completed security scan, independent human audit or production assurance statement. The source review initially found issues; the resolutions and test evidence are recorded in docs/REVIEW_RECORD.md.

| Component | Source | Responsibility |
|---|---|---|
| Supported launcher | cedar/__main__.py:23 | Loopback binding and one worker |
| Browser/API boundary | cedar/app.py:49 | Host, origin, body-size, session, CSRF and role handling |
| Source ledger | cedar/ingest.py:84 | Confined corpus reads and exact UTF-8 source hashes |
| Policy engine | cedar/engine.py:9 | Applicability, dates, uncertainty, evidence types and comparators |
| State and approvals | cedar/store.py:45 | Write transactions, expected revisions and role authorization |
| Export | cedar/export.py:359 | Bounded archive/citation verification without member extraction |

### Effective resources

| Workflow | Resource or capability | Configuration and precedence | Effective location | Readers/writers or recipients | Enforcing control |
|---|---|---|---|---|---|
| Supported CLI | Server socket | --port, default 8765 | IPv4 loopback only | Local browser and local processes | cedar/__main__.py:24-29; one worker |
| Factory | Corpus | CEDAR_CORPUS, otherwise repo/data/full | Selected existing corpus | Loader reads, store copies | cedar/app.py:43-45; missing corpus fails |
| CLI | Corpus | --scope full or slice sets CEDAR_CORPUS | repo/data/full or repo/data/slice | Same loader | cedar/__main__.py:17,26 |
| Factory/CLI | Database | CEDAR_DB or repo/runtime/cedar.sqlite; CLI --db overrides | Local SQLite file | Server and ordinary host filesystem principals | cedar/store.py:26-36; existing row takes precedence over startup fixtures |
| Loader | Supplier text | Catalog document paths, resolved against corpus | Descendant paths only | Corpus author to ledger and public local readers | cedar/ingest.py:93-98 |
| Loader | Declared structured inputs | Only advisories.json, assurance.json and listed-package inventory files | Confined descendants, including resolved symlinks | Assurance engine and export | cedar/ingest.py:106-114 |
| Schema validation | Official schema files | Repository vendor directory | vendor/*.schema.json | Offline validator | cedar/assurance.py validator; no network schema lookup configured |
| Analyst import | New source text | Generated document ID; submitted filename is metadata | SQLite JSON, no filesystem upload destination | Analyst writes; local readers/export consumers read | cedar/store.py upload |
| Export | Portable ZIP | Selected stored snapshot | In memory, returned to local caller | Reviewer with artifact copy | cedar/app.py export; cedar/export.py build_package |
| Verification | Archive members | User-selected package | Bounded memory, no extraction/execution | Local verifier process | cedar/export.py verify_package |

The ASGI factory does not enforce socket binding itself. Operators who launch it through another command own that deployment choice. The documented CLI is the supported local mode.

## Threat model, trust boundaries and assumptions

Protected assets are the documentary decision record, source provenance, uncertainty labels, cost and scoring results, local role authority, and the ability to distinguish a current approval from a historical one.

A document author controls prose and labelled assertions. That author does not acquire policy or reviewer authority by writing instructions in a document. An analyst can import source text through the permitted route but cannot call reviewer-only or approver-only store actions. A hostile webpage can attempt requests to the loopback service; it does not have the same-origin session write token. A package supplier can provide arbitrary ZIP bytes to the verifier. A local operator with filesystem write access can alter source, schemas or the database; the prototype does not isolate itself from that authority.

Public demonstration passwords intentionally allow the operator to exercise all three roles. This is permission enforcement under server-resolved sessions, not proof of three separate human identities. All read endpoints are local-public by design. Real confidential or controlled technical data is outside the demonstration's boundary.

Key invariants:

- A mandatory requirement cannot pass solely because the supplier has a high preference score.
- Missing, contradictory, malformed or wrong-type evidence cannot silently become documentary support.
- An expired/superseded assertion stays inspectable and cannot support the current conclusion.
- Document prose cannot alter comparison policies, sessions or approval state.
- Mutations check the expected input revision under the SQLite write lock.
- Approval requires a current snapshot and a current technical review referring to its record digest.
- Changes invalidate old approvals; exports preserve the old inputs and identify the historical status.
- HTML is escaped, CSV formula prefixes are neutralized, archive paths are constrained, and source filenames are generated.
- Only declared structured sources enter snapshots; sessions and server secrets are not snapshot fields.

Source evidence: cedar/engine.py assess; cedar/store.py:45-61,171-192; cedar/app.py:53-92; cedar/export.py _sources, _csv_cell, _semantic_errors and verify_package. Tests exercise these contracts in tests/test_engine.py, test_api.py, test_state.py, test_export.py and test_review_regressions.py.

Assumptions include a trusted repository and pinned dependencies, a trusted single host and SQLite file, an operator-owned synthetic corpus, and a separately trusted verifier for adversarial artifacts. Sessions are in memory, expire after eight hours and disappear on restart. The database retains input history; the application does not provide encryption, backup orchestration, tenant separation or tamper-resistant logging.

## Attack surface, mitigations and attacker stories

The following are threat scenarios, not claims of unremediated vulnerabilities.

| Priority | Scenario and capability gain | Prerequisites | Impact | Existing controls and evidence | Additional mitigation for a pilot |
|---|---|---|---|---|---|
| High decision integrity | A document tells an assistant to approve a bid | Analyst imports attacker-controlled text | Unauthorized compliance/approval conclusion if text were authority | Deterministic labelled parser; no live model; instructions inert. test_normalization_citation_and_injection and test_upload_rejection_and_inert_instruction | Keep future model output proposal-only; log real outputs and evaluate injection attempts |
| High decision integrity | A malformed observation disappears beside a passing claim | Same requirement appears in current source with indeterminate validity | False eligibility | Undated assertions preserve uncertainty; review regression reproduces and checks fix | Human annotation of edge cases and stronger source-format validation |
| High decision integrity | Component aliases or conflicting exposure statements hide an issue | Valid inventory or current supplier clarification | Buyer misses a software support question | Match bounded PURL identity before display name; contradictory exposure unresolved; regression tests | Full package identity library, nested-component traversal and application validation |
| High decision integrity | Amendment races with approval | Concurrent authorized requests | Apparently current approval for old evidence | BEGIN IMMEDIATE, expected revision and current digest checks; two race tests | Durable identities, audit service and transaction/load testing |
| Medium local authority | Browser or analyst attempts approver-only action | Valid analyst session or hostile origin | Improper approval | Server role comparison, same-origin/CSRF checks, HttpOnly SameSite cookie; test_server_permissions_csrf_and_stale_revision | Production identity provider and organizational separation of duties |
| Medium artifact integrity | ZIP member escapes destination or expands excessively | Malicious ZIP sent to reviewer | File write/code execution or memory exhaustion if unsafe extraction occurred | Verifier does not extract/execute members, rejects duplicate/unsafe names and excessive expansion; export tests | Establish trusted verifier distribution and operator resource limits |
| Medium data handling | Hidden file or sensitive runtime field enters export | Operator places unrelated file nearby or malformed record passed to exporter | Accidental disclosure | Structured-input allowlist, resolved containment, strict snapshot field sets; relevant regression/export tests | Customer-approved schema, redaction review and data retention policy |
| Medium rendering | Source content becomes HTML/script or spreadsheet formula | Crafted supplier values | Active content when reviewed | Escaped HTML, literal text viewer, CSP and formula-safe CSV; export/API tests | Cross-browser/accessibility review and application security assessment |
| Low availability in this scope | Repeated authorized imports grow the database | Local demo credentials or host access | Disk/memory consumption | Per-request 250 KB and per-source 100 KiB limits; no whole-workspace quota | Add quotas, rate limits and monitoring for any multi-user deployment |
| Trust limit | Attacker recomputes every package hash | Full artifact control | Internally consistent forgery | Explicit authenticity disclaimer; no signature claim | Trusted distribution, signed manifests and identity governance if required |

An unchanged exposure statement in an amendment does not silently inherit an old structured source link. AMD01 and AMD02 intentionally leave the old link stale, producing an unresolved disposition and a change-log entry. An explicit new version-bound declaration is needed. This conservative policy is documented, not an inference of actual application exposure.

## Severity calibration

Critical would require a demonstrated path from this local tool into high-consequence systems or secrets outside its stated boundary; none is established, and there is no aircraft connectivity. High decision-integrity impact would mean an unconditional recommendation or apparently current approval over unsupported or changed inputs. Medium impact includes an unauthorized role action, misleading advisory omission, disclosure of permitted local data or unsafe artifact handling within a real pilot. Low impact includes bounded nuisance or presentation defects that do not alter the decision.

These are contextual examples, not assigned vulnerability severities. Public demo passwords, operator write access to the repository, unchanged status in an exported historical file and absent live model behavior do not by themselves establish a security defect. Moving to confidential multi-user operation changes the assumptions and requires a new assessment.

Repository: 8e9b52eca9ae6ce3906e0fe81d5f36dbb3b9f2dd1de28154bb9e800a5a160767
Version: 473f535751c21281de02c4298155924c44b4aa54a4a684f81d5bce77e2ee443d
