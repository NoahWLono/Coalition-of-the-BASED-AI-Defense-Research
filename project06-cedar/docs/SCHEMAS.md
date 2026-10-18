# Evidence, requirement and snapshot schemas

The precise field/API contract is in [CONTRACT.md](CONTRACT.md). This document explains its meaning. Runtime validation of HTTP objects uses Pydantic with unknown fields rejected. The checked-in corpus is trusted fixture configuration; arbitrary external requirement-schema import is not implemented.

A requirement has a stable `Rxx` ID; exact wording; category; version; mandatory/scored/informational mode; applicable package IDs; an explicit reason for exclusions; accepted evidence types; units; comparator and target; effective/expiry dates; source/reason; and a scored normalization rule where applicable. Switching from v1 to v2 changes a declared support-duration threshold. The previous policy remains in existing snapshots.

An assertion has an ID derived from document ID, content hash and starting line. It records supplier/configuration, document ID/version/hash, line range, literal original text, raw and normalized value, original and normalized units, transformation, evidence type, extraction status, interpretation review and dates. Unknown interpretations are explicit. Superseded and rejected assertions stay in the ledger but cannot provide current support.

| Assessment state | Meaning |
|---|---|
| Supported | Current supplied evidence of the required type supports the comparator |
| Not satisfied | Current interpretable evidence fails the declared comparator |
| Unresolved | Missing, rejected, malformed, ambiguous or insufficient-type evidence |
| Conflicting | Current interpretable sources disagree on value or normalized unit |
| Stale | Policy is not effective, or all matching usable observations are outside their date range/superseded |
| Not applicable | Configuration is outside an explicit applicability list; reason is displayed |

Precedence is applicability, policy date, usable current observations, conflicts, interpretation/evidence-type/unit checks, then comparator. A valid current assertion can replace expired evidence. Equal claims from several sources are not treated as independent confirmations. A declaration cannot satisfy a requirement demanding an independent test. In this corpus, even an `independent_test` is a fictional document category.

Eligibility requires every applicable mandatory assessment to be supported. Preference scoring happens separately. For scored numeric criterion value x, the higher-is-better score is `100 * clamp((x-low)/(high-low), 0, 1)`; lower-is-better reverses the fraction. Unresolved/conflicting/stale scored evidence spans `[0,100]`. Applicable criterion weights sum to one. There is no midpoint imputation. Requirements use their declared category: R19, R20, R21, R22, R24, R25, R29 and R30 form the capability group; R23, R26, R27, R28, R31 and R32 form the service group; profiles give these groups raw weights 1:1, 3:1 or 1:3. Sensitivity checks ratios 0.25, 0.5, 1, 2 and 4. A possible leader's upper bound reaches the greatest lower bound; a guaranteed leader's lower bound exceeds every other upper bound. These comparisons are not probabilities.

Dominance is conservative and criterion-wise: both alternatives must be documentary-eligible and have closed cost bounds; the dominant bid's cost upper bound must not exceed the other's lower bound, and every criterion lower bound must meet the other's upper bound, with at least one strict improvement. Missing costs or overlapping criterion bounds prevent a dominance claim.

A decision snapshot contains application/schema version, timestamp, input revision, evaluation date, selected policy, source bodies and hashes, inventories/advisories/exposure inputs, assertions/reviews, assumptions, preference policy, evaluation/clarifications, chosen package, decision type and rationale. Its canonical JSON digest binds this record. Technical review and approval are separate timestamped events referring to that digest. A conditional decision can approve a documented hold for clarification; it never converts failed gates into unconditional eligibility.

The export adds an envelope status measured at export time. Its manifest hashes files, and the verifier checks sources and citations against the exact snapshot. It does not recompute purchasing truth or guarantee that a package remains current in an external workspace. `scripts/reproduce_decision.py` separately re-evaluates the recorded inputs with this version of the engine.
