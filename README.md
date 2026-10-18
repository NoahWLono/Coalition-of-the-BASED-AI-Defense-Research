# Coalition of the BASED: AI Defense Research

A portfolio of local research laboratories, reproducible experiments, and evidence reviews. Each project has its own source, fixtures, run instructions, and account of what its results establish.

## Projects

| Project | Open the project | Delivered result and limits |
|---|---|---|
| 16 · Ground-control alarm and handover laboratory | [README and run instructions](project16-ground-control-lab/README.md) | Three interfaces for ten fictional civilian incidents. All 1,749 model/render checkpoint records match the declared expectations. Human workload and operational safety remain unvalidated. |
| 18 · Civilian medical-delivery dispatch simulator | [README and run instructions](project18-medical-dispatch/README.md) | Synthetic dispatch simulation, MILP optimization, independent schedule checks, and tiny exhaustive references. Saved baseline optimum applies to the declared integer-slot model; some sensitivity solves retain gaps. No clinical or operational validation. |
| 24 · Geolocation uncertainty laboratory | [README and run instructions](project24-geolocation-lab/README.md) | Synthetic 2D geometry, ambiguity exploration, conservative grid covers, and held-out checks. Bounds are numerical; no formal floating-point certificate or real-world geolocation validation. |
| 31 · Prozorro comparable-purchase analyzer | [README and run instructions](project31-prozorro/README.md) | Completed comparability-audit fallback over 50 real civilian A4-paper lots. Economic screening remains unvalidated: zero eligible comparisons, zero real leads, and no independent human holdout labels. |

The autopilot-failsafe laboratory and Project CEDAR are awaiting their originating chats' final handoffs. They will be added only after those chats finish and their deliverables have been checked. A finished chat can deliver a bounded or partial result; the project descriptions retain that distinction.

## Start locally

```sh
git clone https://github.com/NoahWLono/Coalition-of-the-BASED-AI-Defense-Research.git
cd Coalition-of-the-BASED-AI-Defense-Research
```

Then follow a project's README. Projects run independently and have different dependency requirements. The geolocation lab now lives in `project24-geolocation-lab/`; run its commands from that folder.

The ground-control and geolocation projects have interactive local applications. Medical dispatch has a saved HTML results viewer alongside its CLI and scientific reports. Prozorro includes separate real-data and synthetic HTML reports. GitHub displays HTML source; open these reports locally or use the loopback server described in the relevant README.

## Appearance

Every published project's browser interface opens in **Dark** mode and provides a **Theme** selector with **Dark**, **Light**, and **System**. The browser saves the choice when local storage is available. System follows the operating-system preference. Controls and evidence displays use the selected palette; the original static scientific figures and historical screenshots retain their recorded colours.

## Evidence and scope

[Publication verification](docs/publication-verification.md) records the theme checks, packaging checks, and saved evidence used for this portfolio update. Project-specific tests, reports, provenance, and SHA-256 manifests remain inside each project. Run hash checks from that project's directory.

The collection contains research prototypes. Each project's own model, data provenance, validation limits, and source/reuse notes govern how to interpret and reuse it. Synthetic results do not establish field performance. The Prozorro project uses redacted public-field extracts with source attribution and explicitly withholds unsupported comparisons.

Local virtual environments, browser downloads, caches, credentials, and duplicate project archives are excluded from the repository. Historical machine usernames, absolute home paths, and hostnames have been replaced with publication placeholders where recorded; versions, test outcomes, and scientific results are retained.
