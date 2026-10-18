# Public evidence derivative

The evidence in this public repository is a privacy-redacted derivative of the recorded SITL experiment. The private originals remain byte for byte unchanged in their separate local project. This publication step did not execute the simulator again, change the scenario corpus, or create new experimental observations.

ArduPilot SITL read the host machine identifier through the read-only host filesystem. It included that identifier in startup status messages, the MAVLink `AUTOPILOT_VERSION.uid2` field, and onboard DataFlash messages. Run metadata also contained the host name and original local filesystem paths. The public copy replaces those identifiers while retaining the recorded experiment.

The machine identifier becomes the fictional 32-character value `00000000000000000000000000000011`. The host name becomes `failsafe-lab`; recorded project paths become `/research/project11-autopilot-failsafe`, and other home-directory paths become `/home/researcher`. These values identify this demonstration only.

## Format and measurement preservation

The [redaction script](../scripts/sanitize_publication.py) reads from a separate original tree and writes the public evidence tree. It never prints or saves the original identifier values. Its checks use the pinned pymavlink environment.

- Each timestamped MAVLink record is framed and parsed before modification. Only the host identifier in `STATUSTEXT.text` and the identifier prefix in `AUTOPILOT_VERSION.uid2` may change. The actual recordings contain 17 identifier characters followed by a NUL in the 18-byte `uid2` field. The replacement retains that NUL and the original on-wire length.
- Modified MAVLink packets receive recomputed CRCs using their message-specific CRC extra. Every original and derivative packet must decode with a valid CRC. Record timestamps, sequence numbers, source-system and component IDs, packet lengths, and every other decoded field must match. The firmware commit in `flight_custom_version` remains unchanged.
- DataFlash receives only a same-width replacement of the full identifier. Both complete logs are decoded and compared record by record. Only the corresponding `MSG.Message` text may change. All other fields, including mode, arming state, sensor values, parameters and timestamps, must match. Matching NaN values continue to represent unavailable measurements.
- Text metadata receives the declared hostname and path replacements. Fault events, parameter snapshots, executed scenarios, state observations and deadlines retain their recorded values.

The [machine report](../evidence/publication-redaction.json) records each changed file's original and derivative SHA-256 hashes, packet and log message counts, the permitted changed fields, evaluator comparisons, the residual-identifier scan and the final recheck of the private originals. Original hashes are provenance commitments. They do not make the original private bytes publicly available or prove their authenticity.

## Seals and report references

Each public `SHA256SUMS` seals the derivative files and preserves the original member list. These are new publication seals. The report separately records the original seal hash and the derivative seal hash; it does not represent the derivative as unchanged raw evidence.

Aggregate JSON reports and JSON-formatted captured stdout whose input or seal hashes referred to changed files receive corresponding derivative hashes. The mapping updates exact hash tokens until references converge. The original commitments remain in the redaction report. Experimental measurements and interpretation text are retained. Subsequent offline verification reports explicitly identify their public-derivative scope.

The original corpus retains its 55 passing runs, two expected disabled-failsafe failures and one text-assertion failure. The four affected traces pass the separate corpus 1.0.1 retrospective replay. These outcomes remain separate, as in the original experiment. A complete evaluator-output comparison checks all fields, including the state, fault, timing, parameter and deadline evidence used by the evaluator.

## Reproduce or check

The ordinary offline commands in the README validate the published derivative seals, evaluate the saved observations, and check provenance and isolation records. They do not require the original host identifiers. The public script's synthetic regression checks run with:

```sh
.venv/bin/python scripts/test_sanitize_publication.py
```

Recreating this exact derivative additionally requires the separate private original evidence and the machine-identifier file from the recorded host. Those inputs are intentionally absent from the public repository:

```sh
.venv/bin/python scripts/sanitize_publication.py --source-root /private/original-project --destination-root /public/project --machine-id-file /private/recorded-machine-id
```

Future published runs use an explicitly fictional machine-identifier file and namespace hostname. They produce new evidence directories and do not overwrite these historical records. The redaction check establishes measured equality of the original and public observations under the stated transformations; it is not flight-safety validation, qualified human certification or an independent-machine reproduction.
