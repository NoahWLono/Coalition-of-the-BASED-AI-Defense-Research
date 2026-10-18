# Proposed four-week CEDAR pilot

**For discussion · No customer, access arrangement, budget or engagement is assumed**

The pilot would evaluate whether a procurement team can use CEDAR to trace a comparison to its evidence, identify unresolved mandatory requirements and review amendments consistently. Reduced document-search effort and clearer decisions are hypotheses to measure. The pilot would not authorize a purchase or certify a supplier.

The proposed boundary is one civilian purchasing comparison: three to five configurations, twenty to forty requirements, and at most sixty approved source documents. It would include at least two historical or synthetic amendments. The customer would choose a completed or non-operational example so that pilot output cannot be mistaken for a live sourcing decision. Expansion beyond this boundary requires a revised scope.

## Inputs and responsibilities

| Participant | Required contribution |
|---|---|
| Customer procurement lead | Define the decision, supply approved requirements and cost assumptions, identify material questions, and review the final recommendation format. |
| Customer technical reviewer | Define acceptable evidence, annotate selected passages and requirement outcomes, adjudicate disagreements, and review missed or incorrect gates. |
| Customer data/security owner | Confirm permission to use each input, approve redaction and storage, and decide whether the proposed environment is suitable before any customer material is copied. |
| Noah and the agreed implementation team | Configure the bounded corpus, document changes, run repeatable evaluations, maintain an issue log and deliver the results. Staffing and Noah's specific implementation duties would be agreed before kickoff. |

Required inputs are a versioned requirements table, approved source documents, a documented preference policy, explicit cost assumptions and a named reviewer for ambiguities. No production credentials, aircraft access or vendor-system access are required. The current parser accepts labelled UTF-8 text; any conversion or manual mapping must preserve the original permitted source and be logged as preparation effort. Arbitrary PDF extraction is not an existing feature.

## Weekly work and review points

| Week | Work and deliverable | Review gate |
|---|---|---|
| 1: define the comparison | Freeze scope, data permissions, evidence types and success criteria. Establish a human-reviewed reference set and reserve a held-out subset. Observe and time a small manual comparison using the same tasks. Deliver an input register and evaluation protocol. | Procurement and technical leads approve the requirements and annotations; the data owner approves the handling plan. Without these approvals, continue with synthetic data only. |
| 2: map and evaluate evidence | Import the approved text inputs, record preparation effort, inspect extraction failures and compare assessments with human annotations. Deliver an error register with denominators and source examples. | Review every mandatory false pass and unsupported citation. Fix or explicitly disable unsafe mappings before decision exercises. Keep the held-out subset unopened for tuning. |
| 3: exercise review and change | Run cost checks, preference scenarios, a deliberately incomplete offer and two amendment stories. Exercise analyst/reviewer/approver restrictions, stale approvals and exports. Deliver a traceable sample decision package. | Customer reviewers reproduce selected calculations and follow each material citation. All approval and amendment gates below must pass. |
| 4: assess usefulness and next steps | Evaluate the frozen version on the held-out subset; repeat the defined review tasks with CEDAR. Record errors, task completion, preparation and review time. Deliver the comparison report, limitations, source/code versions and continuation decision. | Joint review accepts the evidence report, records unresolved issues and chooses stop, revise or a separately scoped next phase. |

## Acceptance gates

These are proposed pilot criteria, to be confirmed in week 1. They are not existing customer results.

1. Every assessed input and requirement is versioned and permitted for use. Every material citation in the exported sample resolves to the exact recorded passage; unsupported material citations must be zero in the reviewed set.
2. No unconditional eligibility outcome has an unmet, unresolved, conflicting or stale mandatory gate in the human-reviewed evaluation set. All mandatory disagreements are reported with their denominators and disposition. A small set passing this gate does not establish general accuracy.
3. All selected fleet-cost calculations match separately prepared arithmetic under the same assumptions. Unknown required costs stay visibly open. Score and weight changes reproduce the documented formulas.
4. Analyst approval attempts fail at the server. Both amendment exercises make the earlier decision stale. A competing update cannot leave an approval represented as current over changed inputs. A new snapshot requires deliberate technical review and approval.
5. The exported package passes consistency verification and can be inspected by a reviewer outside the running application. The report distinguishes a conditional hold from eligibility and states the export-time limit of current status.
6. The final report includes extraction coverage and errors, gate errors, unresolved cases, citation errors, and preparation/review effort. Results are separated by development and held-out subsets. No savings target is assumed: a measured benefit must include preparation and correction effort.

Human annotations may disagree. Record those disagreements before adjudication rather than treating the application output as the answer key. Results from one customer's held-out documents apply to that bounded evaluation. General market performance remains unmeasured.

## Data handling and access boundary

Begin with synthetic inputs. Permitted customer inputs would be redacted, non-sensitive materials that the customer is entitled to share, after the data owner approves the handling plan. Remove personal information, credentials, sensitive locations and unnecessary commercial details before transfer. Record the permitted purpose, access list, storage location, retention deadline and deletion owner. Validate redaction on the transferred copy.

The current demonstration has public role credentials, public local read endpoints and no encrypted document store or durable identity provider. It must remain on loopback with synthetic material until the approved pilot environment and any necessary access controls are in place. A trusted host, protected storage and actual access restrictions must be agreed; changing a demo password alone does not establish a suitable environment. Do not send inputs to a model API or external service under this proposal.

Controlled technical data, classified material, confidential supplier information and operationally sensitive customer files are excluded. Admitting any such category would require a separate future access, legal and security plan and a new scope; this proposal grants no permission to handle it. At completion, follow the agreed retention/deletion plan and record disposition of source copies and exports.

## Effort assumptions, dependencies and exclusions

Illustrative planning ranges are **12–20 implementation days** and **4–8 combined customer-review days** over four calendar weeks. They assume one workflow, promptly available reviewers, the volume above, supplied requirements and manually prepared permitted text. Pricing and staffing would be agreed separately; no customer budget or willingness to pay is assumed. Report actual effort weekly. Delayed permissions or major conversion work may reduce scope or require a revised schedule.

The pilot excludes operational deployment, enterprise identity integration, procurement-system connectors, OCR development, autonomous purchasing, aircraft connectivity, live vulnerability scanning, certification, legal classification, formal proof and claims of physical performance. It includes no vendor contact or external publication. Any later model integration needs separate authorization and evaluation of actual outputs.

Continuation would require passing the material safety and integrity gates, manageable errors on the held-out subset, and reviewer evidence that the workflow helps enough to justify its preparation and review cost. The next phase would then have a costed integration and security plan, a broader evaluation set and named operational owners. Unresolved mandatory false passes or misleading approval status would stop adoption until corrected and re-evaluated.
