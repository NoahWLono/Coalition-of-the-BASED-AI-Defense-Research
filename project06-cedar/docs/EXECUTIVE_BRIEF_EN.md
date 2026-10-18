# CEDAR: evidence behind a procurement decision

**Local portfolio demonstration · Synthetic civilian inspection packages**

A low quotation is difficult to compare with a more complete offer when support terms disagree, a required component is unpriced, or a claimed capability lacks the required evidence. Procurement managers need a defensible comparison. Engineering reviewers need the exact passages behind each assessment. Program managers need to see which unresolved conditions could change cost, eligibility or approval.

CEDAR is a locally runnable workbench that organizes those relationships. Its fictional buyer is evaluating six-unit, unarmed UAV packages for civilian inspection. The full corpus contains six suppliers, twelve configurations and forty requirements, supported by thirty-six base documents in three text layouts. Three amendments and two requirement versions exercise change review. Every supplier, product, test passage and advisory is synthetic.

The application extracts explicitly labelled statements, preserves their source version, content hash and line location, and checks them against documentary requirements. Eighteen mandatory gates determine eligibility for further consideration. Fourteen scored criteria express preferences separately; eight informational requirements add context. Missing or conflicting evidence stays visible. Costs use a declared three-year, pre-tax CAD baseline, with quoted escalation and explicit replacement assumptions. Unknown required costs remain open exposures.

The demonstration starts with P01, whose CAD 113,700 known subtotal excludes an unpriced mandatory component. Its evidence also contains a quantity conflict, insufficient support and the wrong evidence type for a required test. A higher preference score cannot remove these gates. P03 initially meets the documentary requirements. When amendment AMD01 reduces its support commitment from 36 to 24 months, CEDAR changes the assessment and marks its previous approval stale. A newly approved conditional record authorizes only the recorded hold for clarification.

The initial full-corpus evaluation matched all 480 requirement states and twelve cost totals in a separately authored expected-results manifest. The executable walkthrough also checks role separation, approval invalidation and package verification. Both implementation and annotations were AI-assisted; these checks establish consistency on a synthetic corpus, without human benchmark validation or independent audit.

The parser handles the documented text grammar. Arbitrary PDFs, OCR and live model evaluation are unperformed. Public demonstration accounts do not authenticate real reviewers. Hashes preserve inspectable consistency; they do not establish supplier truth, field performance or legal compliance.

A proposed four-week pilot would test one bounded purchasing comparison using approved, redacted, non-sensitive documents and human-reviewed annotations. It would measure extraction errors, missed gates, citation accuracy and review effort before deciding whether further integration is justified. Noah Weinberger supplied the project direction and background in AI red teaming, policy analysis and data provenance. Customer validation and contractor endorsement have not occurred.

See the [pilot proposal](PILOT_PROPOSAL.md), [technical case study](CASE_STUDY.md) and [limitations](LIMITATIONS.md).
