# Coalition of the BASED: AI Defense Research

A portfolio of local research laboratories, reproducible experiments, and evidence reviews. Each project has its own source, fixtures, run instructions, and account of what its results establish.

## Projects

| Project | Open the project | Delivered result and limits |
|---|---|---|
| 1 · Autopilot failsafe laboratory | [README and run instructions](project01-autopilot-failsafe/README.md) | Twelve scenarios on pinned ArduCopter 4.5.6 and 4.5.7. Original 58-run results: 55 passes, two expected disabled-failsafe failures, and one preserved text-assertion failure. Corpus 1.0.1 passes retrospective replay of four affected traces; no fresh full run or flight-safety validation is claimed. |
| 2 · Ground-control alarm and handover laboratory | [README and run instructions](project02-ground-control-lab/README.md) | Three interfaces for ten fictional civilian incidents. All 1,749 model/render checkpoint records match the declared expectations. Human workload and operational safety remain unvalidated. |
| 3 · Civilian medical-delivery dispatch simulator | [README and run instructions](project03-medical-dispatch/README.md) | Synthetic dispatch simulation, MILP optimization, independent schedule checks, and tiny exhaustive references. Saved baseline optimum applies to the declared integer-slot model; some sensitivity solves retain gaps. No clinical or operational validation. |
| 4 · Geolocation uncertainty laboratory | [README and run instructions](project04-geolocation-lab/README.md) | Synthetic 2D geometry, ambiguity exploration, conservative grid covers, and held-out checks. Bounds are numerical; no formal floating-point certificate or real-world geolocation validation. |
| 5 · Prozorro comparable-purchase analyzer | [README and run instructions](project05-prozorro/README.md) | Completed comparability-audit fallback over 50 real civilian A4-paper lots. Economic screening remains unvalidated: zero eligible comparisons, zero real leads, and no independent human holdout labels. |
| 6 · CEDAR · Procurement and assurance workbench | [README and run instructions](project06-cedar/README.md) | Synthetic civilian procurement demonstration with six fictional suppliers, twelve packages, forty requirements, versioned evidence, enforced review roles, amendment staleness, and verified decision exports. Customer validation, live model evaluation, physical product tests, production identity, and digital signing remain unperformed. |

Projects are numbered 1–6 in the order shown above. The folders use zero-padded numbers so they sort in the same order. Historical source records retain their original task identifiers: 11 → 1, 16 → 2, 18 → 3, 24 → 4, 31 → 5, and CEDAR → 6.

All six originating chats completed their final handoffs before import. A finished chat can deliver a bounded or partial result; the project descriptions retain that distinction.

## Start locally

```sh
git clone https://github.com/NoahWLono/Coalition-of-the-BASED-AI-Defense-Research.git
cd Coalition-of-the-BASED-AI-Defense-Research
```

Then follow a project's README. Projects run independently and have different dependency requirements. The geolocation lab now lives in `project04-geolocation-lab/`; run its commands from that folder.

The ground-control, geolocation and CEDAR projects have interactive local applications. Autopilot and medical dispatch have saved HTML results viewers alongside their command-line tools and scientific reports. Prozorro includes separate real-data and synthetic HTML reports. GitHub displays HTML source; open these reports locally or use the loopback server described in the relevant README.

## Appearance

Every published project's browser interface opens in **Dark** mode and provides a **Theme** selector with **Dark**, **Light**, and **System**. The browser saves the choice when local storage is available. System follows the operating-system preference. Controls and evidence displays use the selected palette; the original static scientific figures and historical screenshots retain their recorded colours.

## Evidence and scope

[Publication verification](docs/publication-verification.md) records the theme checks, packaging checks, and saved evidence used for this portfolio update. Project-specific tests, reports, provenance, and SHA-256 manifests remain inside each project. Run hash checks from that project's directory.

The collection contains research prototypes. Each project's own model, data provenance, validation limits, and source/reuse notes govern how to interpret and reuse it. Synthetic results do not establish field performance. The Prozorro project uses redacted public-field extracts with source attribution and explicitly withholds unsupported comparisons.

Local virtual environments, browser downloads, caches, credentials, and duplicate project archives are excluded from the repository. Standalone environment metadata uses publication placeholders. Autopilot telemetry is supplied as an explicitly documented redacted derivative, with fictional machine identity and refreshed evidence seals; private originals are retained locally. Versions, test outcomes, and scientific results are retained.

The repository includes approximately 647 MiB of recorded simulator evidence as redacted publication copies, including raw telemetry and DataFlash logs. Firmware executables are fetched by the pinned bootstrap script rather than stored in Git. CEDAR retains its recording, PDFs, screenshots and verified decision packages. Its duplicate whole-project ZIP can be generated locally.
