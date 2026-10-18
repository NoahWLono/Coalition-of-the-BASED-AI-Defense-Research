# CEDAR product brief and acceptance design

A procurement manager needs a comparable six-aircraft fleet price and a shortlist whose mandatory gates cannot be hidden by a preference score. An engineering reviewer needs the exact passage, source version, units, evidence type and unresolved interpretation behind each assessment. A program manager needs the open cost exposures and a precise explanation of which conclusions and approvals changed after an amendment.

CEDAR organizes the evidence behind a procurement comparison, identifies unresolved requirements, makes assumptions visible, and preserves a reviewable decision history. Reduced repeated searches, consistent comparison rules and easier amendment review are proposed benefits, not measured outcomes.

The authoring direction is Noah Weinberger's supplied specification, informed by his stated interests in AI red teaming, policy, provenance and formal methods. Implementation, synthetic data and annotations are AI-assisted. No employer, contractor relationship, field validation or independent audit is asserted.

Implementation choices by the assistant: Python/FastAPI, SQLite and plain browser JavaScript; deterministic extraction of three documented text layouts; no live LLM, OCR, PDF ingestion, exchange rates, signing or formal proof. A local, CPU-only workbench makes these boundaries visible. Six fictional suppliers offer two configurations each. Forty requirements comprise 18 gates, 14 scored criteria and eight information requests. CAD and an explicit three-year six-unit baseline simplify review.

The first milestone has three bids, eight requirements, missing mandatory evidence, a conflict, an amendment, cost calculation, role-separated review and portable export. Only after its verified workflow is recorded does the dataset and interface expand. The full milestone adds 36 base documents, three amendments, two requirement versions, 12 inventories, sensitivity, an evidence matrix, change review and the portfolio materials.

Acceptance follows the twelve criteria in USER_REQUEST.txt. Evidence must include an executable test record, a separately authored expected-results manifest, literal arithmetic checks, UI screenshots, a reproducible package and an honest limitations statement. Recommendation means documentary eligibility for further consideration only. No actual product capability is established.

Visual direction: pale slate #f3f6f8, deep navy #142d42, ink #213747, teal #167c80, amber #ac6916, white #ffffff. System sans typography, compact tabular numbers, left aligned text. A persistent navigation rail, wide requirements table and evidence drawer put the commercial comparison at the center. Small state markers use words as well as color. The evidence drawer is the central visual feature; decoration stays quiet.

See ../../CONTRACT.md for schemas, parser grammar, API and concurrency semantics. The application is local and synthetic. No external writes or publication are authorized.
