# Stage, unit and comparability contract v1

Written before the fifty-record import on 2026-10-17 America/Toronto.

## Scope and provenance

The demonstration targets A4 copier/printing paper published from 2025-01-01 through 2025-03-31. It is a bounded convenience sample, not a census or a representative sample. Ordinary civilian education, health, culture, local administration and civilian utility buyers are eligible. Defense, police, security, emergency-service and unknown buyers are excluded. Buyer classification is assistant-produced and provisional. Do not retain contact details, addresses, coordinates, supplier identities or reconstruct hidden data.

Each source extract retains the public tender UUID, public tenderID, source URL, retrieval time, response SHA-256, extract SHA-256, source modification time and creation/publication evidence. API v2.5 public GET is the acquisition interface. Full responses are parsed transiently and immediately projected to allowed fields. A hash of the response does not mean the full response was retained. Public document metadata/references are permitted evidence; contents require separate review. Attribution: Prozorro, https://prozorro.gov.ua/openprocurement. Reuse statement and acquisition failures belong in the acquisition ledger.

## Identity and accounting

A purchase candidate is one `(tender UUID, explicit lot ID)` pair. When no lots exist, use the explicit synthetic identifier `single` for the tender-wide lot. This does not assert that the API published an explicit lot. A multi-lot tender with unresolved item/award/contract links is excluded, never allocated proportionally. Feed revisions are deduplicated by tender UUID. Fifty means fifty unique lot keys, not fifty amounts or stages.

Retain observations separately: estimate, bid, award, contract_current, amended_contract and payment_observed. A contract API snapshot is current state at acquisition, not the original signed state. `value.amount` is a total in the stated currency; it is not automatically paid expenditure. `amountPaid` is a reported aggregate payment, not an independently reconciled cash transaction. Missing payments are unknown. Preserve cancelled observations and exclude cancelled lots from purchase screening. Amendments and changed quantities require reconciliation before selection. Missing or masked zero quantities remain unresolved; never substitute one.

Only one reconciled active current contract per lot can enter purchase screening. Do not combine an award amount with a tender quantity without explicit evidence that they cover the same goods and quantity. Do not select among multiple active contracts by lowest price or latest date. Store original decimals as strings and compute with Decimal. No binary-float accounting.

## Unit rules

Canonical unit is one sheet of A4 paper. Explicit sheets convert by factor 1. Explicit thousand sheets convert by 1000. Explicit packs convert using a reviewed sheets-per-pack count; a stated 500-sheet pack converts by 500. Thousand packs convert by 1000 times the reviewed pack size. Boxes, pieces, lots, services and conflicting code/name pairs require review. An item description mentioning 500 sheets does not prove that a quantity measured as pieces denotes packs. Accept one decimal mark (comma or point), optional space grouping; reject mixed/ambiguous separators, non-finite, zero and negative inputs. No inferred currency, tax rate, package size or missing quantity.

Mixed goods and bundled services are excluded unless separately priced and quantity-linked in the same procurement stage. This prototype conservatively excludes multiple item lines. CPV alone and string similarity alone cannot establish equivalent quality. A4 size, grammage, sheet count, whiteness/grade/brand or a reviewed equivalence judgment must be supported.

## Comparison gates

An eligible group requires reviewed and evidence-linked: goods specification equivalence, canonical quantity, currency, fiscal treatment (including VAT inclusion and resolved net/gross scope), delivery cost inclusion and delivery/service terms, payment terms, procurement stage and quantity version. The review ledger must identify annotator type: assistant, independent human, or synthetic fixture author. Missing values never form an 'unknown equals unknown' group. Assistant review is provisional; only independently reviewed real records may generate validated real screening leads. The program can report provisional arithmetic separately with no economic comparison claim.

Within eligible records, group by exact goods-specification key, currency, fiscal key, delivery key, payment key, stage, publication month and volume band (less than 50,000 sheets; 50,000 to 499,999; at least 500,000). Different currencies are excluded from the real demonstration. No currency conversion is performed. NBU reference rates, date, currency units and tax handling would need a separate explicit conversion contract before cross-currency comparisons. Common FX rescaling is a mathematical invariance test, not empirical FX validation.

## Screening and evaluation

Choose the algorithm only after this contract is recorded. Screening is subordinate to the gates. Use a minimum group size and a transparent robust threshold with sensitivity analysis; never call a lead corruption. Export all exclusion reasons and stage observations, including records without computable prices. Preserve review strata: ordinary, bundle, missing quantity, amendment, cancelled, suspected extreme arithmetic value. An empty observed stratum is explicitly empty, not filled with invented real records.

Separate holdout labels from screening inputs. Human-reviewed true unusual prices, legitimate differences and valid exclusions are needed for precision, false-lead proportion, false-positive rate and false-exclusion rate. Zero labels produces null metrics and an unmet validation gate, not zero errors. Report denominators and binomial uncertainty. Synthetic expectations test code only. Independent rational arithmetic can verify calculations but cannot verify economic comparability or substitute for human review.
