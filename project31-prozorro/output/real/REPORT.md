# Prozorro civilian paper comparability audit

The saved demonstration contains 50 unique public lots from January through March 2025. 1 have a computable active-contract price under the strict stage and unit rules. 0 pass all comparison gates, and 0 real screening leads are emitted.

The result is a comparability audit. It does not establish that the screening method is useful. Independent holdout labels accepted from supplied provenance: 0. precision: unavailable (numerator 0, denominator 0, Wilson 95% interval None). false_lead_proportion: unavailable (numerator 0, denominator 0, Wilson 95% interval None). false_positive_rate: unavailable (numerator 0, denominator 0, Wilson 95% interval None). false_exclusion_rate: unavailable (numerator 0, denominator 0, Wilson 95% interval None).  Exclusion records a limit in the available evidence. It does not establish that a purchase was wrong.

Publication-window membership uses API dateCreated and is checked against the public tender identifier. Contract and payment records are current at acquisition, potentially amended after the reporting period. The sample was found through public search and is not representative. Each tender contributes one explicit lot or one documented tender-wide `single` lot.

Amounts retain their original procurement stage. Reported amountPaid values are not independently reconciled cash payments. A terminated contract is preserved but excluded by this prototype's active-contract screening policy. Mixed item lines and unverified package conversions remain unresolved. Net and gross values, VAT flags and currencies are never inferred.

## Data-quality reasons

Counts overlap because each lot may have several unresolved gates.

| Reason | Lots |
|---|---:|
| currency_unknown | 23 |
| delivery_evidence_missing | 50 |
| delivery_unknown | 50 |
| fiscal_evidence_missing | 50 |
| fiscal_unknown | 50 |
| independent_human_review_required | 50 |
| item_link_unresolved | 10 |
| multiple_items | 16 |
| no_active_current_contract | 23 |
| pack_size_unreviewed | 13 |
| payment_evidence_missing | 50 |
| payment_unknown | 50 |
| price_unavailable | 49 |
| quantity_evidence_missing | 50 |
| quantity_version_unknown | 10 |
| review_unapproved | 50 |
| spec_evidence_missing | 50 |
| specification_unknown | 50 |
| stage_evidence_missing | 50 |
| unit_unresolved | 13 |

## Reproduction and evidence

Run `bash scripts/reproduce.sh` from the project directory. It runs the offline test suite, rebuilds this report from retained public extracts and checks exact rational arithmetic. `provenance.json` binds each row to an extract hash, source-response hash, public API URL and acquisition time. `stage-observations.csv` preserves amounts by stage. `report.html` supplies per-lot evidence panels and public document-metadata references. Source: [Prozorro](https://prozorro.gov.ua/openprocurement), reused with attribution under its observed public open-data statement.

`assumption-sensitivity.json` shows unsupported package-size stress tests separately from baseline results. Nine screening-threshold combinations are in `screening.json`. Empty lead sets cannot establish robustness when groups are ineligible. UAH is the only permitted real comparison currency; no FX rates were applied.

## Validation still required

Independent review must cover original records and contract documents, goods quality, quantity versions, fiscal treatment, delivery costs, payment terms and holdout labels. Record evidence and reviewer identity for every accepted review. Supplied review assertions remain subject to provenance verification. The evaluation function computes proportions and Wilson intervals only when the relevant denominators exist. Those intervals do not correct this sample's selection bias.

Synthetic fixtures exercise packaging, decimals, missing taxes, cancellations, amendments, duplicate stages, screening and evaluation behavior. They are separate from the fifty-lot real dataset and cannot establish real-world error rates. No procurement actor is accused of wrongdoing.
