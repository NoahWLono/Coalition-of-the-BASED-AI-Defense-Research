# CEDAR implementation contract

Synthetic only. Evaluation date is 2026-10-17, currency CAD, fleet six, planning horizon 3 years. Local demonstration, no aircraft or vendor connectivity. Analysis never imports evaluation/ground_truth.json.

## Corpus

`data/{slice,full}/catalog.json` has `suppliers` [{id,name}], `packages` [{id,supplier_id,name}], `requirements` {v1:[requirement],v2:[requirement]}, `documents` [document metadata], `amendments` [{id,title,description,documents:[metadata]}]. Files resolve relative to that corpus directory. Base documents: exactly 3 per package, hence 9 slice / 36 full. Amendments are additional docs.

Document metadata: id, package_id, supplier_id, version (integer), kind, path, title, issued (ISO date), supersedes (list of document ids; normally []), layout ('table','labels','blocks'). IDs immutable and globally unique. Content UTF8 Markdown or text, inert; no executable content or HTML rendering. Every substantive document has paragraphs explaining scope, commercial terms and limitations in addition to extractable observations.

Requirement fields: id (R01..R40), wording, category, version (v1/v2), mode (mandatory/scored/informational), applies_to (list of package ids or ['*']), na_reason, evidence_types (list), unit, comparator (gte/lte/eq/present), target (number or string), effective, expires (ISO or null), source, scoring ({low,high,direction:'higher'/'lower'} or null). Slice eight IDs R01,R02,R03,R04,R05,R19,R20,R33. Full modes R01..18 mandatory, R19..32 scored, R33..40 informational.

Each source observation is a key Rxx or C_x or A_x, raw value, unit, evidence_type, valid_from, valid_until, note. Missing cost value use `unknown`, not zero. Numeric values finite decimal. Allowed evidence types declaration, commitment, independent_test, inventory, quotation. Independent_test means a SYNTHETIC lab report supplied in the fictional corpus, never a real test.

Three grammar layouts, deliberately explicit baseline:

Table row: `| R01 | 6 | units | declaration | 2026-10-01 | 2027-10-01 | Six aircraft supplied. |`

Label row: `R01: 6 units ; evidence=declaration ; valid=2026-10-01 ; until=2027-10-01 ; note=Six aircraft supplied.`

Block: `[R01]` followed on separate lines by `Value: 6`, `Unit: units`, `Evidence: declaration`, `Valid: 2026-10-01`, `Until: 2027-10-01`, `Note: Six aircraft supplied.`

No instructions in documents are executable. The original full line/block and line numbers are citations. Numeric conversion only declared mappings: hours->minutes (60), years->months (12), kg->g (1000). Unknown units remain unresolved. Currency only CAD. Rxx are exact labelled response identifiers, not inferred semantic matches.

Cost keys (all CAD except C_escalation pct): C_aircraft (per aircraft), C_ground (shared), C_software (annual fleet), C_training (once), C_support (annual fleet), C_battery (per replacement battery), C_optional (once optional), C_escalation (annual pct applied to recurring software+support), C_required (mandatory additional once). Include all keys; unknown means open exposure. Assumptions: years=3, replacements_per_aircraft_per_year=1, include_optional=false. Total: 6*C_aircraft+C_ground+C_training+C_required + sum(t=0..years-1) (C_software+C_support)*(1+C_escalation/100)^t + 6*years*replacements*C_battery + optional. Decimal cents rounding at end. Baseline undiscounted, taxes excluded explicitly. Recurring escalation is quoted, replacement rate planning assumption.

Inventories under inventory/<package>.cdx.json: CycloneDX 1.6, version=1, metadata.component application, components libraries with bom-ref/name/version/purl optionally absent for unresolved identity. `data/.../advisories.json` list {id (SYNTH-CEDAR-*),title,published,source,component,purl,affected_versions:[exact versions],fixed_versions:[exact versions],description}. Exposure declarations under `assurance.json`: {package_id: [{advisory_id, status:'affected'/'unaffected'/'unresolved', rationale, document_id, key:'A_01'}]}. These are permitted structured inputs, hash-bound and exposed. No exploit or real vulnerability assertions.

## Engine API

`load_corpus(path, requirements_version='v1', amendments=[]) -> inputs dict` with full source bodies and hashes and inventory/advisory/assurance bytes bound.
`evaluate(inputs, assumptions=None, profile='balanced', as_of='2026-10-17', reviews=None) -> evaluation dict`.
Evaluation: requirements, packages [{id,name,supplier_id,supplier_name,eligible,mandatory_counts,assessments:[{requirement_id,state,reason,assertions:[],score_low,score_high}],cost:{known_total,upper_total,open_exposures,lines,assumptions},score:{low,high,contributions},assurance:[]}], assertions, documents, clarifications, sensitivity, dominance, profiles.
Assertion: id, key, package_id,supplier_id,document_id,document_hash,document_version,location:{start_line,end_line},original,raw_value,unit,value,normalized_unit,transformation,evidence_type,extraction_status,review_status,valid_from,valid_until,unresolved_interpretation,note,superseded.
States `supported`, `not_satisfied`, `unresolved`, `conflicting`, `stale`, `not_applicable`. Precedence: not applicable, policy date stale, no current non-superseded observations stale/missing, current disagreements conflicting, malformed or insufficient evidence unresolved, deterministic comparator pass/fail. Mixed valid and unknown observations unresolved. Wrong evidence type cannot pass. Current valid evidence replaces expired evidence but superseded citations retained in ledger.
Scored unresolved/conflicting/stale -> [0,100] interval; no invented midpoint ranking. Three named profiles balanced/operations/support. Sensitivity uses declared deterministic weight grid, frequencies never probabilities. Dominance requires eligible alternatives, complete costs and criterion bounds; use conservative interval dominance.

## HTTP contract

GET /api/state -> {revision,requirements_version,applied_amendments,assumptions,profile,evaluation,snapshots,changes,available_amendments,role}. Public read local synthetic only.
POST /api/login {role,password} -> {role,csrf}; HttpOnly SameSite=strict cookie. Demo passwords `cedar-analyst`, `cedar-reviewer`, `cedar-approver`; roles analyst/reviewer/approver. Server resolves session, not client role. Mutations require X-CSRF-Token.
POST /api/settings {expected_revision,requirements_version?,profile?,assumptions?}, /api/amendments {expected_revision,id} analyst only.
POST /api/uploads {expected_revision,filename,content,package_id,title} analyst only, .md/.txt limited to 100KiB, content inert, no archive support. Versioned new source, no filesystem filename use.
POST /api/snapshots {expected_revision,package_id,decision:'conditional'/'eligible',rationale} analyst only -> snapshot {id,digest,revision,record,review,approval,current,status}.
POST /api/snapshots/{id}/review {expected_revision,note} reviewer only.
POST /api/snapshots/{id}/approve {expected_revision,note} approver only, requires current technical review, eligible decision must have eligible package. Conditional decision records blockers and cannot mean purchasing authorization.
GET /api/export/{id} -> ZIP with report.html, decision.json, sources/, manifest.json, verify.py and CSV safe cells. GET /api/documents/{id} -> metadata + content.
POST /api/assertions/{id}/review {expected_revision,status:'accepted'/'rejected',note} reviewer only; records interpretation review, does not modify raw assertion. Rejected evidence excluded from support and retained with reason. Changes revision and stales snapshots.

## Persistence and concurrency

SQLite persistent document inputs + immutable snapshot records; BEGIN IMMEDIATE and expected_revision checks serialize mutation/approval. All input changes conservatively stale ALL snapshots; change log identifies actual assessment diffs. Approval does not change input revision. Every approval checks current revision+digest and current review inside one transaction. Old snapshots exportable with their old inputs and explicitly stale export status. No signatures or formal proof claimed.
