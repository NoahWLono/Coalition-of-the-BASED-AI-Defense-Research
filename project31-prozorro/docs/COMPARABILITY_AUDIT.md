# Fifty-lot civilian paper comparability audit

Prepared on 17 October 2026, America/Toronto. The procurement window is 1 January through 31 March 2025. The retained source state was acquired on 18 October UTC, still 17 October in Toronto.

The project delivered the import pipeline, fifty real normalized lot records, source and exclusion ledgers, an evidence report, and executable verification. **The full screening milestone remains unmet.** The available extracts and assistant inspection do not establish document-supported comparison groups, and no independent human holdout labels were supplied. The permitted comparability-audit fallback applies. No real price-difference or misconduct finding is asserted.

## Acquisition and accounting

The importer retained fifty unique lot keys from fifty civilian tenders after rejecting twenty-five candidates. Discovery combined public search results and published links from the official website. Search indexing and deliberate edge-case selection affect the sample. It cannot estimate market-wide frequencies. Ordinary paper procurement can appear under broader office-supply CPV codes, so descriptions and buyer scope were also checked.

The instrumented acquisition made 125 serial public GET requests, all with HTTP 200, receiving 5,862,526 bytes. This count covers procurement acquisition, separate from the documented source-research requests and initial endpoint probes. Fifty tender extracts and fifty linked contract snapshots were retained as permitted field projections. Twenty-five rejected candidate responses were not retained as procurement extracts. Full raw responses were hashed and discarded after projection.

The records contain 50 estimates, 61 bid observations, 51 award observations, 48 current-contract observations, 2 amended-contract observations and 27 reported-payment observations. These 239 stage observations belong to fifty lots. They are not 239 purchases. A reported aggregate payment can explicitly be zero; its absence remains unknown.

Current API and document versions are recorded in [the source ledger](source-acquisition-ledger.json). [Prozorro's reuse statement](https://prozorro.gov.ua/openprocurement) permits reuse of public open data with attribution. The implementation applies additional privacy and scope exclusions. It does not reconstruct wartime redactions. Original document metadata is linked, but contract document contents have not been independently reviewed.

## What the retained evidence supports

| Observation or check | Result |
|---|---:|
| Real unique lots | 50 |
| Multiple-item bundles | 16 |
| Single-item sheet quantities unresolved by the independent audit | 26 |
| Amended contracts | 2 |
| Embedded active contract versus detailed terminated status | 22 |
| Exact total divided by the contract's own declared quantity | 34 |
| Of those quotients, terminated-contract snapshots | 17 |
| Explicit recognized sheet conversion in snapshot arithmetic | 8 |
| Strict active-contract sheet price accepted by normalization | 1 |
| Fully eligible comparison groups | 0 |
| Independently reviewed real holdout labels | 0 |

Counts describe different overlapping conditions. A declared-unit quotient can be arithmetically correct while the unit, quality, taxes or delivery terms remain unsuitable for comparison. The strict screen intentionally excludes terminated contracts and unreconciled amendments. This prototype policy does not establish that those contracts are invalid.

The one strict selected price is supported by 3,345 UAH divided by 25 explicit 500-sheet packs: 12,500 sheets and exactly 669/2500 UAH per sheet, or 0.2676. Its source is [the published contract record](https://public-api.prozorro.gov.ua/api/2.5/contracts/344cf1d050944677ad03edf43e5a7214). Independent integer/Fraction arithmetic matches the normalizer's Decimal result. This establishes that division for the retained source snapshot. It does not establish economic comparability with another purchase.

One inspected snapshot records 65,000 UAH and 650 explicit 500-sheet packs, while its detailed contract status is terminated and amountPaid is explicitly zero. The audit preserves all three observations. Dividing the contract value by sheets would not establish paid expenditure. See the field paths and source references for tender `267f363647dd4effa708852c3c981854` in [the assistant inspection ledger](../data/assistant-review.json).

## Review, sensitivity and evaluation

Fourteen cases were selected for assistant inspection across ordinary cases, bundles, ambiguous units, amendments, status differences and arithmetic extremes. All 104 evidence paths resolve to the retained source extracts. The missing-numeric-quantity and cancelled-lot strata are empty in this real sample. Synthetic fixtures exercise those cases; they are not substituted for real observations or human review.

The independent arithmetic checker uses a separate integer/Fraction implementation and imports neither the adapter nor the normalizer. It matched the sole strict price and reported no source-coverage or exact-value mismatch. This provides methodological independence for arithmetic. Both the source inspection and the code were produced by assistants; no qualified or independent human validation is claimed.

The baseline keeps missing pack sizes and ambiguous piece units unresolved. Sensitivity runs separately assume 500-sheet packs or interpret single-item piece quantities as 500-sheet packs. They change how many arithmetic prices can be produced. They still produce no eligible real groups because the other evidence gates remain unresolved. These deliberately unsupported stress assumptions are never used in baseline results.

The screen tests nine threshold pairs and uses groups of at least five compatible records. Its median/MAD rule requires both statistical deviation and a price-ratio threshold. A zero-MAD group uses a separately labelled ratio rule. Six synthetic records produce exactly the expected one lead; common currency scaling preserves that synthetic result. UAH is the only real comparison currency, so empirical FX-conversion sensitivity was not performed.

Precision, false-lead proportion, false-positive rate and false-exclusion rate are all **unavailable**, with numerator zero, denominator zero and no confidence interval. These values are null in [evaluation.json](../output/real/evaluation.json). Zero emitted real leads is not evidence of zero false-flag risk. The code computes Wilson intervals when reviewed denominators exist, but this sample cannot establish the method's usefulness.

## Verification and remaining gates

The final software suite covers acquisition boundaries, privacy-field projection, decimal and thousand-unit arithmetic, missing taxes, bundles, cancellations, amendments, stage deduplication, package ranges, conflicting lot links, failed current-contract reads, conflicting VAT assertions, reporting and evaluation. Code review findings were reproduced with failing tests and corrected. The full executed result is in [verification.txt](../evidence/verification.txt).

The next required work is independent document review. Verify goods quality, package interpretation, contract quantity versions, fiscal scope, delivery inclusion and payment conditions. Resolve the relevant source conflicts, record reviewer provenance, and label a holdout without tuning the screen to those labels. Then recompute the groups and error rates with explicit denominators and uncertainty. The delivered tool supports that process but does not certify the truth of user-supplied review assertions.

No repository push, publication, deployment, payment or contact with procurement participants occurred. The offline replay requires only Python's standard library. Browser preview attachment failed in this session, so HTML content and escaping were verified programmatically; visual browser QA remains unverified.
