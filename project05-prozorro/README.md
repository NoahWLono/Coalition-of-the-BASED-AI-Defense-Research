# Project 5: Prozorro comparable-purchase analyzer

This project is numbered 5 in the public portfolio. Historical task records retain the original project 31 identifier.

This local Python project imports public civilian A4-paper procurement records, preserves their accounting stages and withholds price comparisons when the terms are unresolved. The delivered dataset contains **50 real lots created from 1 January through 31 March 2025**. It is a search-discovered convenience sample.

**The delivered result is a comparability audit. Screening remains unvalidated.** One record supports a strict active-contract price per sheet. None passes every document and independent-review gate. No real economic screening leads are issued. Precision and false-exclusion rates are unknown because no independent human holdout labels were available.

Open [the evidence report](output/real/report.html), [the audit findings](docs/COMPARABILITY_AUDIT.md), or [the normalized dataset](output/real/normalized.csv).

Both [the real report](output/real/report.html) and [the synthetic fixture view](output/synthetic/report.html) open in dark mode. Their labelled Theme selector offers System, Light and Dark. The browser remembers the choice when local storage is available; System follows changes to the operating-system preference. The report remains usable when storage is blocked. Tables, evidence panels and status text use the selected theme, and printed reports use light colors.

## Reproduce locally

Python 3.11 or later is required. The implementation uses the standard library; no installation, API key or paid service is needed. Python 3.14.8 was used on the observed Arch Linux host.

```sh
cd project05-prozorro
bash scripts/reproduce.sh
```

Run the first command from the portfolio checkout, or skip it when already inside this project directory.

The explicit Bash script also works when launched from Fish. It runs tests, rebuilds the real and separate synthetic reports, independently recomputes selected arithmetic with rational numbers, and verifies artifact hashes and sample boundaries. Reproduction makes no network requests. The development session used a model service and public web access; this is not a claim of an offline AI workflow.

To regenerate just the real report:

```sh
env PYTHONPATH=src python3 -m prozorro_compare report
```

To regenerate the separate synthetic JSON and HTML exercise without network access:

```sh
env PYTHONPATH=src python3 -m prozorro_compare demo
```

To resume explicit public acquisition, preserving existing extracts:

```sh
env PYTHONPATH=src python3 -m prozorro_compare acquire --target 50 --request-cap 150
```

The saved sample already has fifty records, so this command performs no requests. Acquisition accepts only the official HTTPS read endpoints, uses serial requests, caps each response at 5 MB, and stops on 401, 403 or 429. The cap is per invocation; the delivered acquisition used 125 requests across three invocations, below the planned total of 150. No API mutation exists in this program.

## Files and evidence

| Deliverable | Location |
|---|---|
| Current source, reuse and redaction research | [docs/source-research.md](docs/source-research.md) |
| Documentation acquisition evidence | [docs/source-acquisition-ledger.json](docs/source-acquisition-ledger.json) |
| Procurement request ledger | [evidence/acquisition.jsonl](evidence/acquisition.jsonl) |
| Preserved public field extracts | `data/extracts/`, 50 JSON files |
| Stage, unit and comparison rules | [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md) |
| Typed normalization and screening | [src/prozorro_compare/core.py](src/prozorro_compare/core.py) |
| Dataset and individual evidence panels | [output/real/report.html](output/real/report.html), [normalized.json](output/real/normalized.json), [normalized.csv](output/real/normalized.csv) |
| Stage observations and exclusion ledger | [stage-observations.csv](output/real/stage-observations.csv), [exclusions.csv](output/real/exclusions.csv) |
| Assistant inspection of 14 selected cases | [data/assistant-review.json](data/assistant-review.json) |
| Separate rational arithmetic reconciliation | [evidence/reconciliation.json](evidence/reconciliation.json) |
| Evaluation and assumption sensitivity | [evaluation.json](output/real/evaluation.json), [assumption-sensitivity.json](output/real/assumption-sensitivity.json) |
| Reserved, unlabelled holdout template | [holdout-review-template.json](output/real/holdout-review-template.json) |
| Synthetic screening exercise | [output/synthetic/report.html](output/synthetic/report.html), [checks.json](output/synthetic/checks.json) |
| Executed verification and versions | `evidence/verification.txt`, `evidence/environment.json`, `evidence/commands.md` |

Full source responses were processed transiently, hashed, and reduced to permitted comparison fields. Their original bytes were not retained. The extracts and their hashes are retained. Contacts, suppliers, addresses, coordinates and signature content are omitted. A free-text pattern check adds a limited safeguard; it does not certify that every future text field is free of personal information. Public document metadata points to original records; document contents were not independently reviewed.

Publication copies of retained logs replace absolute home-directory paths with `<HOME>`, and the environment snapshot omits the hostname. These metadata redactions leave the recorded test and audit outcomes unchanged.

Source attribution is **Prozorro**. Its [official developer page](https://prozorro.gov.ua/openprocurement) permits public open-data reuse with attribution. The source ledger records the successful check and distinguishes the API URL version 2.5 from observed deployed application version 2.7.47. The code has no FX conversion path. UAH is the only permitted real comparison currency.

## Review and evaluation workflow

The next step is an independent review of original contract documents. Resolve specification equivalence, quantity versions, package units, fiscal scope, delivery costs and payment terms. The provided assistant inspection is provisional. Keep a holdout for evaluation separate from the records used to settle comparison rules.

Comparability review input is a JSON object keyed by `tender_uuid/lot_id`, with each value matching the `Review` type in `core.py`. The caller must supply true provenance, evidence for every gate and `annotator_type: independent_human`. The software checks required fields. Reviewer identity and evidence quality require external verification. A source conflict remains excluded even if a review assertion disagrees.

Holdout input uses the supplied template and requires explicit `comparable` and, when comparable, `unusual` judgments with source evidence. Only independently reviewed real labels enter empirical metrics. Rebuild using:

```sh
env PYTHONPATH=src python3 -m prozorro_compare report --reviews reviews.json --labels holdout.json --output output/reviewed
```

The immutable delivered baseline remains in `output/real`. New review assertions alone cannot repair unsupported quantities or amendments: evidence-supported adapter inputs or a separately reviewed extension are required. The prototype excludes multiple item lines, unreconciled amendments and terminated contracts from strict screening. Wilson intervals describe the labelled cases and do not remove sampling bias. The sample does not support a population corruption or overpricing estimate.
