# Synthetic corpus annotation notes

The fixture author is an assistant task separate from the implementation task. The author prepared package stories, expected requirement states, and literal cost arithmetic before comparing them with engine output. The author did not import the engine to create the answer key. This separation helps detect implementation errors; it is not independent empirical confirmation or human validation.

The initial scope has three packages, eight requirements, nine base documents, three CycloneDX inventories, and one amendment. The full corpus was generated after the implementation task reported that the complete slice walkthrough and its thirty-six tests passed. Each source contains fictional commercial prose and exact response labels. These labels are a deliberately constrained extraction baseline. Success on these fixtures says nothing about extraction accuracy on arbitrary customer documents.

The buyer is the fictional Cedar Civil Inspection Service. Supplier and laboratory names, product capabilities, prices, advisory identifiers, and events are invented. The supplied `independent_test` entries describe fictional laboratory memoranda. No physical test was conducted and no real product capability is established. Component advisories are invented procurement fixtures and contain no exploit.

## Authored slice outcomes

| Package | Intended outcome | Commercial consequence |
| --- | --- | --- |
| P01 Alder Survey Lite | Battery conflict, short support, no acceptable independent-test evidence | Cheapest known-cost floor is incomplete and cannot justify eligibility |
| P03 Birch Inspect Standard | All eight requirements supported under v1 | Eligible before AMD01, subject to the limits of synthetic documentary evidence |
| P05 Cobalt Terrain Base | Expired delivery commitment and ambiguous endurance unit | Delivery blocks eligibility; endurance retains a score interval |

R02 for P01 has both eighteen batteries in the specification and twelve in the quotation. Both claims are current and neither supersedes the other. R03 commits to twenty-four months when the buyer requires thirty-six. R04 is explicitly a supplier declaration even though its numerical value would otherwise pass. These are separate defects, so repairing one must not erase the others.

P03 states support in years, endurance in hours, and payload in kilograms. The declared conversions yield 36 months, 45 minutes, and 1200 grams. AMD01 replaces the complete support document, retains its other response fields, and withdraws the thirty-six-month support commitment in favour of twenty-four months. R03 must change to not satisfied. The old source and any approval based on it must remain inspectable, with the previous approval marked stale.

P05's delivery commitment expired on 2026-09-30. Evaluation is fixed at 2026-10-17. Its endurance unit `flight-units` is undefined, so the engine must not infer minutes from context. The intended score interval is 0 to 100 for that criterion.

## Arithmetic independent of the engine

The comparison uses six aircraft, three years, one replacement battery per aircraft per year, no optional carrying-case upgrade, no taxes, and no discounting. These are buyer planning assumptions. A projected recurring payment does not extend the supplier's contractual support period.

P01 has CAD 113,700 of known cost: `84,000 + 6,000 + 1,500 + 15,000 + 7,200`. Its mandatory charger/interface kit is unpriced. The known figure is a floor; the upper total remains unresolved.

P03 totals CAD 153,654.48: `111,000 + 8,000 + 2,400 + 1,000 + 7,200 + 7,416 + 7,638.48 + 9,000`. Recurring fees are CAD 7,200 in year one and escalate by three percent annually.

P05 totals CAD 137,686.56: `99,000 + 7,000 + 1,800 + 2,200 + 6,400 + 6,528 + 6,658.56 + 8,100`. Recurring fees are CAD 6,400 in year one and escalate by two percent annually. Rounding occurs only at the final cents result.

## Untrusted and structured inputs

P01's quotation contains an assistant-directed instruction to approve the supplier. It is an adversarial sentence in an inert document. It must not change extraction rules, evidence requirements, role permissions, or decisions.

Inventories, synthetic advisories, and exposure declarations are permitted structured inputs. The source terms contain matching A_01 declarations, and the structured file identifies that document and response key. Unresolved component identity must remain visible. A component's presence alone does not establish application-specific exposure; a supplier's unaffected declaration is also not independent validation.

`ground_truth.json` is an evaluation artifact. Runtime ingestion must not load it. Human review of the annotations, real customer-corpus evaluation, and live-model extraction evaluation have not been performed.

## Full corpus authored outcomes

The full corpus has six fictional suppliers, twelve packages, forty requirements, thirty-six base documents, three amendments, and twelve inventories. Requirement modes are eighteen mandatory, fourteen scored, and eight informational. Two requirement versions differ in the support commitment: v1 requires thirty-six months; v2 requires forty-eight months. In the full scope v2 takes effect on the evaluation date, 2026-10-17.

The full answer key was written before generating the full source files or comparing them with engine output. It contains 480 expected baseline assessment states and twelve literal cost outcomes. Existing slice stories retain their meanings. The added cases are:

| Package | Authored case | Expected v1 eligibility |
| --- | --- | --- |
| P02 Alder Survey Plus | Current required evidence and complete costs | Eligible |
| P04 Birch Inspect Thermal | Missing R15 maintenance release commitment | Blocked |
| P06 Cobalt Terrain Thermal | Two current R07 minimum-temperature values | Blocked |
| P07 Dovetail Range Standard | Strong operational values and modest support terms | Eligible |
| P08 Dovetail Range Thermal | Unknown R11 encryption setting and mandatory component price | Blocked |
| P09 Elm Survey Standard | Manufacturer declaration substituted for R04 independent-test evidence | Blocked |
| P10 Elm Survey Thermal | Expired R04 report and R26 support-response commitment | Blocked |
| P11 Fenland Service Standard | Strong support terms and moderate operational values | Eligible |
| P12 Fenland Service Thermal | Complete offer with lower scores and greater cost than P11 | Eligible |

R18 applies only to the six even-numbered thermal configurations. The six standard configurations receive not applicable with the explicit reason in the requirement record. Their response schedules retain supplier statements, but applicability is determined by the buyer's policy. All other requirements apply to every package.

P07 reaches the favourable endpoint on every operational criterion. P11 reaches the favourable endpoint on every support criterion and scores forty percent on each operational criterion. Weight changes should therefore change the preferred eligible package between those alternatives under the documented profiles. P12 costs CAD 19,400 more than P11 and is strictly worse on all fourteen scored criteria. This provides a clear conservative dominance example under the buyer's declared criteria. The thermal option receives no unannounced scoring bonus.

AMD02 replaces P04's complete terms document and supplies the omitted R15 commitment. AMD03 replaces P06's complete specification and resolves both R07 values to minus five Celsius. AMD01 retains the slice's support-shortening story. Each replacement repeats every unchanged response from the replaced document. The discarded source versions remain available to the evidence ledger.

Structured assurance declarations intentionally keep their original document references after AMD01 and AMD02. Their A_01 values are repeated in replacement terms, but the original version-bound references must become unresolved when their source is superseded. A separately reviewed structured override would be needed to bind the assurance rationale to a new source version. Repeated text alone cannot silently perform that rebinding. The application has no such override workflow in this corpus.

The full requirements, source files, and hashes are separate from the slice. Document identifiers are stable within each corpus. A document with the same identifier in the slice and full demonstration can have different contents because the full schedule contains additional responses; the corpus scope and content hash must distinguish those inputs.

## Extraction expectations and denominators

`extraction_truth.json` captures the generator's logical observation records before source serialization or engine parsing. Each entry records document, layout, response key, occurrence, raw value, unit, evidence type, and validity dates. This supports exact-match precision and recall by layout. It does not infer expectations from the parser's output, and it is never an application input.

The slice contains fifty-five base assertions: nineteen for P01 and eighteen each for P03 and P05. AMD01 adds four records, with four original records superseded. The full baseline contains 601 assertions: 480 requirement positions plus two extra contradictory claims, minus the deliberately omitted response, plus 108 cost entries and twelve assurance responses. Full layout denominators are 200 table records, 201 label records, and 200 block records. The three amendments add sixty assertions and supersede sixty source assertions.

The generator and the parser were authored in separate assistant tasks using the same model family and shared schema. That separation can expose coding errors; it does not constitute independent human annotation, independent model evidence, or a held-out customer benchmark. The three layouts are known grammars, so their results must be described as synthetic exact-label extraction rather than general document understanding.
