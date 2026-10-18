# Sources and provenance

Sources were consulted on 2026-10-17 in America/Toronto. All scenario labels, values and annotations were produced by assistants for this laboratory. No customer interface, participant data, vehicle log, controlled material or real location was used. Separate oracle authorship reduces implementation coupling but is not independent empirical validation.

| Primary source | Version or date observed | Use in this project |
| --- | --- | --- |
| [W3C WCAG overview](https://www.w3.org/WAI/standards-guidelines/wcag/) | Overview updated 17 September 2026; WCAG 2.2 publication/update dates shown as 5 October 2023 and 12 December 2024 | Selection of accessibility checks; no claim of conformance |
| [W3C ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/) | Current web guide accessed on source date; no release number asserted | Accessible names, native semantics and keyboard interaction |
| [WCAG 2.2: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) | WCAG 2.2 supporting guidance | Visible text for severity, freshness and unresolved responsibility |
| [WCAG 2.2: Keyboard](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html) | WCAG 2.2 supporting guidance | Keyboard-only replay, selection and disclosure checks |
| [WCAG 2.2: Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html) | WCAG 2.2 supporting guidance | Readable focus outline and focus retention checks |
| [PX4 Flight Modes](https://docs.px4.io/main/en/flight_modes/) | `main`, mutable; selector showed v1.17 stable | Background for separating mode from human responsibility; no behavior or API imported |
| [Playwright Library](https://playwright.dev/docs/library) and [Keyboard API](https://playwright.dev/docs/api/class-keyboard) | Documentation accessed on source date; installed library 1.62.1 | Local headless UI inspection and keyboard events |

The app has no PX4, MAVLink, aircraft, radio, external telemetry, authentication or cloud-service integration. Its HTTP server serves local project files to loopback clients. Documentation lookup and AI-assisted authoring used model/service infrastructure, so this work is not described as an offline AI workflow.

The code and original fixtures were authored for this project. No external fonts, icons, screenshots, copied operational layouts or source excerpts are included. Browser tooling is a verification dependency, with its own upstream licensing. No paid API or additional service spend was used.
