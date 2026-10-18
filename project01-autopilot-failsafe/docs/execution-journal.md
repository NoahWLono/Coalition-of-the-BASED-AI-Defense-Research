# Execution journal

The user authorized a bounded local simulator experiment. All installation, implementation and execution stayed within `project11-autopilot-failsafe`. The parent workspace began with an unborn `master` branch and no files; a `codex/autopilot-failsafe-lab` branch was selected. Other project directories appeared while this experiment ran and are outside this project's scope.

Initial inspection used `uname -a`, `free -h`, `df -h .`, `nproc`, executor discovery, Git status and applicable AGENTS.md discovery. The host was Arch Linux x86_64, eight logical CPUs, about 15 GiB RAM with about 8 GiB initially available, and 289 GiB free space. No applicable AGENTS.md was present. An unprivileged user/network namespace probe with `unshare` and a private-device probe with Bubblewrap succeeded. Neither command altered host networking.

Official binary downloads used HTTPS from `firmware.ardupilot.org/Copter/stable-4.5.6/SITL_x86_64_linux_gnu/` and the corresponding 4.5.7 path. Both files were 6,802,848 bytes. The manifest stores their SHA-256 and upstream commit identifiers. A project venv uses Python 3.12.14 and pinned pymavlink. No system packages, services or privileged settings were changed.

## Development attempts preserved

1. `bash scripts/isolated-case.sh --scenario scenarios/00-baseline.json --version 4.5.6 --output evidence/development/baseline-01` failed before telemetry with a simulator segmentation fault. The exact-command debugger trace is `evidence/development/startup-debug/gdb-exact.txt`. It shows `AP_Param::find` called from `HALSITL::Util::set_cmdline_parameters`. Source inspection found that the advertised `--serial9` indexes beyond the nine-entry serial-path array into the adjacent command-line parameter vector. Removing that unused argument resolved this startup failure. There is no hardware serial argument in the runner.
2. `baseline-02` booted but its configuration gate rejected upstream airspeed fields absent from the Copter parameter enumeration. The original upstream defaults remain intact. `config/base-copter.parm` removes only `ARSPD_PIN` and `ARSPD_BUS`; the laboratory settings remain explicit and read back exactly.
3. `baseline-03` attempted arming after a GPS fix but before the estimator accepted position. The autopilot rejected arming with `Arm: Need Position Estimate`. The harness now waits for the EKF absolute-position flag without disabling arming checks or forcing arm.
4. `baseline-04` completed takeoff, a verified stable hover, commanded LAND, and disarming. A separate offline evaluator passed its sealed raw telemetry. This is development evidence; the release suite runs its own fresh baselines.

These attempts identify harness and compatibility problems. They are not successful fault scenarios, independent security findings, or release regressions. The debugger used a private network and device namespace with automatic debuginfo downloading disabled; no crash report was sent.

## Verification method

The runner records raw receive/transmit packets, monotonic host timing, simulator clock values, event dispatch times, exact input configs, full parameter snapshots, sockets, device file descriptors and teardown status. The evaluator reads the sealed packet logs without importing the runner. Artificial evaluator fixtures are labeled synthetic. Negative controls use actual simulator telemetry with a disabled GCS action, and separately replay unchanged logs against an intentionally wrong mode assertion.

Local simulator processing is separate from the model service used to author and inspect this project. This is not claimed to be an offline AI workflow. Assistant-authored assertions and trace annotations are identified as such.

## Completed suite and final evaluation

The full stage ran `PYTHONPATH=src .venv/bin/python scripts/suite.py --stage full --output evidence/full`. Its progress log and per-case commands are retained. All 58 cases completed in 1,902.1 wall seconds. The suite returned exit 1 for one original-corpus text mismatch in addition to the two expected disabled-failsafe controls. No missing simulator run was replaced by a fixture.

Final commands were `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` (41 tests, exit 0), `PYTHONPATH=src .venv/bin/python scripts/summarize.py evidence/full --reevaluate` (all 58 raw traces replayed, exit 1 for the preserved original mismatch), `.venv/bin/python scripts/audit_suite.py evidence/full` (522 provenance/isolation checks, exit 0), `.venv/bin/python scripts/demo.py` (real PASS and qualified wrong-mode FAIL, exit 0), and `.venv/bin/python scripts/review_corpus_revision.py evidence/full` (four assertion-only replays, exit 0). The final evaluator hash and revision differences are recorded in machine-readable reports.

The original corpus 1.0.0 is preserved. Corpus 1.0.1 corrects only the documented GCS/battery text alternatives after source and independent trace review. No simulator event, parameter, deadline, or expected state was changed. Its fresh full execution is proposed as the next external reproduction, not claimed as completed here.
