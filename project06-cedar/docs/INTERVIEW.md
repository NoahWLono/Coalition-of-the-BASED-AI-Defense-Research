# Ten technical questions about CEDAR

These answers describe the implemented local demonstration. Proposed pilot work is labelled separately. Noah supplied the project direction and relevant background; the repository and supporting materials were developed with AI assistance. No manual authorship, customer validation or independent audit is implied.

## 1. What does "supported" establish?

It means that current supplied evidence of an accepted type satisfies the buyer's documentary comparison rule. Each assertion retains the literal passage, document version, SHA-256 hash, line range, normalization and dates. A declaration cannot satisfy a requirement demanding an independent test. Even an `independent_test` passage in this corpus is fictional: it demonstrates an evidence rule. Physical capability remains untested. A real pilot would require the buyer to define acceptable evidence and a qualified reviewer to judge its adequacy.

## 2. How does the system avoid treating missing information as a pass?

The engine distinguishes supported, not satisfied, unresolved, conflicting, stale and not applicable states. Applicability and policy dates come first; usable observations, conflicts, evidence types, interpretation and units are checked before the comparator. Every applicable mandatory requirement must be supported for documentary eligibility. Scoring is separate. Missing scored evidence spans a score interval rather than receiving an invented midpoint. A high score cannot compensate for an unresolved mandatory condition.

## 3. What can the extraction actually read?

The parser recognizes explicit requirement and cost identifiers in three documented UTF-8 text layouts. It retains the source text and applies only declared unit conversions, such as years to months. It does not discover semantic requirement matches, perform OCR or ingest arbitrary PDFs. Unrecognized input may yield no assertion, which leaves the requirement unresolved. An optional proposal-adapter interface exists, but the application has no live model client and no measured model outputs. Representative permitted documents and human annotations are prerequisites for evaluating broader extraction.

## 4. What makes the cost comparison defensible?

It exposes its inputs and uses decimal arithmetic for a six-aircraft fleet. The three-year baseline includes quoted equipment, shared ground equipment, software, training, support, batteries and required additions. Quoted recurring escalation is separate from the planning assumption for battery replacements. Optional items are explicit. The baseline is undiscounted, pre-tax CAD. Unknown required charges have no finite upper bound; P01's CAD 113,700 is a known subtotal. Taxes, currency conversion and financial-policy extensions would need additional declared rules.

## 5. How should a buyer interpret the rankings and sensitivity analysis?

Fourteen criteria use declared min-max formulas, bounded to 0–100. Applicable weights sum to one. The three profiles express balanced, capability and service priorities. Five explicit capability-to-service ratios show which eligible packages could or must lead given their score intervals. These scenarios do not estimate probabilities of purchase success. Dominance requires closed cost bounds and criterion-by-criterion superiority under conservative interval comparisons. In the initial corpus P11 dominates P12 under that definition. These calculations inform a preference discussion; they do not establish a universally best purchase.

## 6. What does software assurance add to a procurement decision?

CEDAR validates the declared CycloneDX 1.6 inventory format and matches a bounded set of synthetic advisories using the fixture identities and exact version lists. It distinguishes component evidence from the supplier's exposure statement, with provenance and dates. Unresolved identity or exposure can justify a clarification or support question. Inventory validity does not establish completeness, shipment contents or exploitability. There are no real CVEs, live scans or real vendor findings, and no opaque aggregate cyber-risk score.

## 7. Can a document or the AI grant approval?

No. Source text is inert data. The demonstrated parser has no authority to execute document instructions, change policy or select a role. The server checks the session role for mutation, technical review and approval actions; it also applies request bounds, origin/host and CSRF checks. The optional model interface is proposal-only and is not called by the application. Public demo credentials demonstrate permission boundaries. They do not establish genuine separation of people. Production identity, storage and tenancy controls remain unimplemented.

## 8. What happens if an amendment races with approval?

Mutations use a SQLite write transaction and check the expected workspace revision under the lock. Approval also checks the snapshot digest, current inputs and required technical review. If the amendment commits first, approval of the old revision fails. If approval commits first, the amendment makes it stale. Invalidation is conservative: every input change stales all previous snapshots. The change log identifies the particular assessments and costs that changed; selective reuse of unaffected approvals is not implemented. AMD01 demonstrates the support reduction from 36 to 24 months.

## 9. How strong are the tests and exported hashes as evidence?

The initial full-corpus evaluation matched 480 requirement states and twelve cost totals against a separately AI-authored manifest. Tests and executable walkthroughs also exercise citations, costs, permissions, concurrency and amendment behavior. Human annotation and independent empirical audit remain unperformed. An export includes the snapshot, sources, evidence index, report and a verifier. Hashes detect internal inconsistencies relative to the manifest; an attacker who replaces both can recompute them. They do not prove authenticity or future approval status. No digital signature or formal proof is claimed.

## 10. What would integration and a credible customer pilot require?

The current architecture is one local FastAPI service, SQLite and a browser client. A four-week pilot would begin with a single permitted, redacted comparison, agreed evidence rules and human annotations, including a held-out subset. It would measure errors and total preparation/review effort and exercise amendment and export gates. Production integration would separately require durable identities, suitable storage, retention, backups, operational monitoring and tested interfaces to the customer's systems. The project has no customer validation, measured time savings or enterprise deployment. Those are questions for the pilot and later phases.

Supporting detail: [schemas](SCHEMAS.md), [architecture](ARCHITECTURE.md), [limitations](LIMITATIONS.md) and [pilot proposal](PILOT_PROPOSAL.md).
