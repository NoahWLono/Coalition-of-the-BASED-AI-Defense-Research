# Focused review and development record

This is an AI-assisted development record. A separate fresh-context agent reviewed the backend source without executing it. The primary agent evaluated the findings and wrote local runtime reproductions. This separation is useful criticism, not independent human validation or independent empirical confirmation. The fixture author separately prepared expected results before engine comparisons.

## First milestone

Local commit `ba6fd37` preserves the first complete slice: three packages, eight requirements, nine base documents, one amendment, versioned source citations, costs, role-separated review and approval, stale-approval behavior and portable export. `artifacts/milestone-a.json` records the API demonstration, and `artifacts/milestone-a-tests.txt` records its 36 passing tests. Later source refinements are covered by the current suite and package regeneration; the original milestone log remains a historical checkpoint.

## Material review findings and resolutions

| Finding | Reproduction | Resolution |
|---|---|---|
| A component display-name alias suppressed a matching synthetic advisory | `test_matching_purl_cannot_disappear_due_to_display_name` failed with no affected issue | Compare bounded package identity before display names; preserve the advisory |
| An invalid date made uncertainty disappear beside valid evidence | `test_undated_evidence_prevents_false_support_and_closed_cost` failed because support remained supported | Indeterminate validity blocks support and closes no cost exposure |
| Assurance transitions were absent from amendment diffs | `test_amendment_logs_software_assurance_changes` failed | Change records now include disposition changes and reasons |
| A second current exposure declaration did not challenge an unaffected disposition | `test_conflicting_exposure_declarations_remain_unresolved` failed | Conflicting current exposure assertions produce unresolved disposition |
| An indeterminate exposure date disappeared beside a valid unaffected statement | test_undated_exposure_cannot_preserve_unaffected_until_rejected failed before the assurance fix | Keep ambiguous dates and their citations; an explicit reviewer rejection can remove that ambiguity |
| Text-mode file reads normalized CRLF before hashing | `test_corpus_hashes_exact_utf8_bytes_and_ignores_undeclared_json` failed | Decode exact UTF-8 bytes without newline rewriting |
| Recursive JSON reads could include unrelated files or follow an external symlink | The two corpus-boundary regression tests failed | Read only declared inventory/advisory/exposure inputs and enforce resolved containment |
| Walkthrough checksum named SHA-256 actually hashed hexadecimal text | Source reviewer traced digest(payload.hex()) | Hash actual ZIP bytes; final release checks compare the reported value with hashlib/sha256sum |
| Missing full-corpus path silently fell back to the slice | `test_missing_requested_corpus_does_not_silently_fall_back` failed | Startup now fails on a missing requested corpus |

The red reproductions are retained in `artifacts/review-red.txt` and `artifacts/startup-red.txt`. The current green result is recorded in `artifacts/test-results.txt`. Early import failures are retained as initial development evidence; they are not presented as successful tests.

Two earlier implementation problems were also resolved: the first advisory pass omitted unidentified components and treated the version suffix of a fixed PURL as a different identity; the corresponding tests now preserve uncertainty and correctly recognize an explicitly listed fixed version. Full-evaluation equality initially depended on the ordering of source metadata in the response; documents are now ordered deterministically and the order-invariance check passes.

## Deliberate decisions and remaining review scope

A source-version change does not silently rebind a structured exposure statement. AMD01/AMD02 leave their old exposure references stale. The resulting unresolved disposition is visible in assurance, clarification and change views. This is a conservative policy; a pilot needs a reviewed workflow for new version-bound exposure declarations.

The source reviewer found no demonstrated bypass of the reviewed role, CSRF or serialized approval checks. That observation is bounded to inspected source and tested scenarios. UI/browser behavior was checked separately after implementation. Public demo credentials, host filesystem authority and absence of real product evidence remain explicit limits.

Assurance is intentionally limited to top-level CycloneDX components, generic PURLs and exact synthetic affected/fixed lists. Nested components, other ecosystems, completeness and shipped-binary attestation require further work. A future-dated advisory now produces an unresolved evaluation rather than silently applying later knowledge.

The reviewer did not judge the then-unfinished interface and portfolio, real-world procurement validity, production identity suitability, model performance or customer adoption. These are addressed by browser checks, documentation and bounded pilot criteria rather than inferred from the source review.
