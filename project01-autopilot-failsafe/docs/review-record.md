# Review record

The evaluator was implemented separately from the controller and does not import its logic. A fresh assistant code reviewer inspected the completed implementation and reproduced two faults using synthetic logs outside the sealed simulator evidence. This is assistant review, not human certification or independent empirical flight validation.

- The original suite accepted any headline FAIL as a detected negative control. A synthetic trace with failed heartbeat silence but a correct LAND response exposed the mistake. The control gate now requires confirmed silence and the intended state mismatch. A wrong-mode replay must fail the altered mode assertion while its other assertions pass. The same qualification governs the comparison report.
- The original field evaluator treated a sparse stream with one healthy reading as a definite failure to cross a threshold. The revised evaluator requires stream coverage to issue a negative determination. Sparse negative evidence is INDETERMINATE; a witnessed matching value still satisfies an existential assertion.

Both issues have regression tests. The suite process had already imported the earlier evaluator when these review fixes landed, so its progress log is preliminary. The final comparison re-evaluates every sealed trace with the final evaluator, records the evaluator hash, and rechecks the intended negative-control mismatches. The final original-corpus evaluation retains every executed expectation. A later, separately versioned text correction is documented below.

The runner also gained an output-path check with two tests to keep generated results inside the project's evidence directory. This does not change simulator commands or fault schedules. Each full-suite run contains its own runner-source.py and exact configuration copies.

Read-only raw-file permissions were added during the full suite. Earlier completed traces receive the same permissions before final replay. This changes storage handling only. Source snapshots in each run show the exact runner revision; simulator arguments, parameter files, fault schedules, physical evidence requirements and expected transitions were held fixed throughout the full suite.

The evaluator also checks that armed GUIDED state persists from the completed baseline until the first fault. A regression test demonstrates that an earlier LAND cannot satisfy a later fault-response assertion. The final 41-test run passed; a source reviewer inspected this guard and the text-alternative implementation.

The completed suite exposed one text assertion that excluded a legitimate battery-first branch. Independent DataFlash inspection and identical pinned source established the reason. Corpus 1.0.1 changes only scenario 11 assertion 02 to permit the two explicit GCS messages. A generic battery-only failsafe message still fails. A separate script verifies that this is the only scenario change and replays all four affected traces without replacing their original results. The original comparison retains its failed gate; the retrospective revision assessment passes. The complete suite was not rerun under the revised corpus.

The reproduction script now continues artifact generation after a suite failure and returns a nonzero status if any stage fails. Provenance/isolation audit success is recorded separately from scenario success. Seven orchestration smoke cases and five audit-expression cases exercised those distinctions using temporary stubs; these are software checks, not additional SITL runs.
