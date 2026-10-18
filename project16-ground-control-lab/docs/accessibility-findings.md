# Accessibility findings

The original light-theme interface passed the bounded keyboard, label, focus, disclosure, grayscale and narrow-viewport checks below in headless Chromium 151.0.7922.34. These are software and visual-inspection findings. They do not establish WCAG conformance or usability with assistive technology.

The theme update adds Dark, Light and System choices through a labelled native select. Dark is the initial setting; saved preferences apply from a blocking script before the stylesheet. System listens for operating-system preference changes. Storage failures leave the page usable. Five Node tests exercise these branches through bounded browser-API adapters. The existing reduced-motion rule and textual severity/freshness cues remain in place. No new browser, assistive-technology or human-participant checks were performed for this update; the saved screenshots and browser reports describe the original light theme.

The current CSS-token contrast check covers 44 selected pairs across dark and light themes. Text and focus pairs range from 5.25:1 upward; control-border pairs meet 3:1, with a minimum of 3.70:1. This includes critical alarms, stale ownership, known-state marks, rejected events and the ownership-detail surface. It is a source-palette calculation, not an exhaustive rendered audit. Results are in [contrast.json](../evidence/contrast.json).

## Executed checks

| Check | Actual evidence | Limit |
| --- | --- | --- |
| Keyboard-only core tasks | Tab, native select arrows and Enter reached scenario/checkpoint/design controls and the owner, next actor, issue and historical-observation answers in all three variants | A scripted path at the interrupted-handover checkpoint; no participant task data |
| Replay controls | Keyboard Play, Reset, step and rewind worked; reset stopped subsequent timer advancement | One browser runtime |
| Focus visibility | The focused design control or disclosure summary had a solid 3-pixel outline | Selected focus states, not an exhaustive screenshot audit |
| Focus stability | Global Play retained focus while replay advanced; an expanded disclosure retained its summary focus during updates | No screen-reader speech observation |
| Accessible names | Interactive buttons, selects, inputs and summaries had names in DOM inspection; an accessibility-tree snapshot was saved | A browser tree is not a screen-reader user session |
| Disclosures | All obscured fact values, labels and timestamps became visible after expansion at every checkpoint; changing incident closed old disclosures | The information can still require scrolling |
| Color independence | Severity and freshness use words and symbols; grayscale preserved Unresolved, unknown, timestamps and next actor | No full color-vision-deficiency simulation or user study |
| Reduced motion | Browser preference set to reduce; CSS disables animation, transitions and smooth scrolling | Replay remains user-controlled temporal content |
| Narrow layout | At 390 by 844 CSS pixels, document width did not exceed the viewport; saved screenshot inspected | Does not replace zoom, text-spacing or a complete reflow audit |
| Original color contrast | Eight authored light-theme solid-color pairs measured 5.72:1 to 12.18:1; focus/paper was 7.48:1 | Superseded by the current CSS-token check above; disabled controls and every rendered state remain outside that bounded check |

See [browser-report.json](../evidence/browser-report.json), [accessibility-tree.txt](../evidence/accessibility-tree.txt), [ui-regression-green.json](../evidence/ui-regression-green.json), [contrast.json](../evidence/contrast.json) and the [screenshots](../screenshots/). `node tools/contrast-check.mjs` reproduces the selected sRGB relative-luminance calculations. The reference sources are listed in [sources.md](sources.md).

## Concrete interaction gaps and design costs

The chronological design requires a disclosure to find the principal issue, next actor, group mapping and historical observation. The grouped design hides transfer phase, target and next actor. The handover design hides receipt and group details. These are intentional differences and remain keyboard accessible, but a person must discover the relevant disclosure. No user observation establishes how easy that discovery is.

The page is long, especially at narrow widths. The three questions in the comparison rail, detailed event history and export buttons can require substantial scrolling. Matrix visibility classifications mean expanded document content, not guaranteed viewport visibility. Several supporting labels are small; enlarged-text and text-spacing checks remain unfinished. A 390-pixel screenshot alone cannot establish low-vision accessibility.

The live region announces selected control actions and phase transitions, while the checkpoint-check status can also update. Speech order, verbosity and interruption behavior have not been assessed with a screen reader. A future assistive-technology check should examine whether those announcements help or compete, and whether moving among native controls and evidence headings is understandable.

No tests were run with Firefox, WebKit, magnification software, voice control, switch access or a screen-reader user. No formal conformance audit was performed. The prototype's optional study materials require accessible training and participant-chosen accommodations before any future study.
