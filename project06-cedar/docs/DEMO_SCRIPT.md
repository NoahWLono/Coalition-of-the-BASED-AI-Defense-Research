# CEDAR: a decision that changes when the evidence changes

**Target: 4 minutes 45 seconds after rehearsal · Synthetic data throughout**

This is a narration script and an executable API walkthrough. It does not claim that a video recording has been made. The live sequence uses the implemented browser interface; the API replay is a separate reproducible fallback.

## Prepare before the meeting

From the repository, install the locked environment and launch a fresh demonstration:

```sh
uv sync --frozen
uv run --frozen python -m cedar demo --db runtime/presentation-01.sqlite
```

Use a new database filename for each clean rehearsal; an existing database retains its decisions and amendments. Open [the local workbench](http://127.0.0.1:8765). Confirm Overview shows twelve configurations, five documentary-eligible configurations, forty requirements in the matrix and no applied amendments. Requirements must be V1, the planning horizon three years, the replacement rate one, and optional equipment excluded. Keep all data synthetic and the server on loopback.

The top-right role button opens the sign-in dialog. Choose a role, enter its displayed password and click **Sign in**. The public passwords are `cedar-analyst`, `cedar-reviewer` and `cedar-approver`. These are shared demonstration identities. The narrated review actions exercise the workflow. Independent human approval has not occurred.

Keep the short notes below ready to paste. Close an evidence or review panel with its top-right close button before changing views or roles. Rehearse the clicks and downloads; the timings allow brief source inspection. A full technical review requires more time.

## 0:00–0:25: Establish the comparison

**Action:** Start on **Overview**. Point to the scope, eligibility count and P01 subtotal. The initial requirements and supplier corpus are imported automatically when the fresh database starts.

**Say:**

> CEDAR compares fictional six-aircraft packages for a civilian inspection buyer. The new workspace has imported twelve configurations and forty requirements. Five configurations currently satisfy the mandatory documentary gates. That means they can receive further consideration; it does not establish field performance or authorize a purchase.

## 0:25–1:10: Inspect the apparent bargain

**Action:** Click **Inspect P01** in the lowest-subtotal callout. Show the open mandatory gates and unpriced required item. Select **R02**, then an assertion card, to show the original passage, lines, version and hash. Close the panel. Open **Requirements matrix**, choose **P01** in **Configuration**, and point to R03 and R04.

**Say:**

> P01 has the lowest known subtotal: 113,700 Canadian dollars. A mandatory component is still unpriced, so the upper total is open. Its current documents also disagree about battery quantity. Here is the actual passage and its source version. Support is too short, and a supplier declaration does not satisfy a requirement for independent-test evidence. A high preference score cannot remove those gates.

## 1:10–1:45: Change an explicit assumption

**Action:** Sign in as **Analyst**. Open **Comparison** and select **P03** in **Inspect configuration**. Show CAD 153,654.48. Change **Replacement batteries / aircraft / year** from `1` to `2`, then click **Save assumptions**. Confirm CAD 162,654.48. Briefly point to **Weight sensitivity** and **Conservative dominance** below the criterion table.

**Say:**

> P03 initially costs 153,654 dollars and 48 cents under the three-year assumptions. Two replacement batteries per aircraft per year raise that to 162,654 dollars and 48 cents. The quotation has not changed; the planning assumption has. Below, the weight scenarios expose preference trade-offs, and the declared comparison shows P11 dominating P12. Those scenarios do not estimate purchase-success probabilities.

## 1:45–2:35: Freeze and review the eligible decision

**Action:** Open **Decision package**. Set **Decision configuration** to P03 and **Decision type** to **Documentary eligible — further consideration**. Paste the first rationale below and click **Create snapshot**. Switch to **Reviewer**, click **Record technical review** on that snapshot, paste its review note and submit. Close the panel. Switch to **Approver**, click **Approve decision**, paste its approval note and submit. Confirm the snapshot badge reads **Approved**.

**Say:**

> The analyst freezes the evidence, assumptions and recommendation in one snapshot. A technical-review role records its review of that exact digest, then a separate approver role approves it. The server enforces these permissions. I am switching shared demonstration accounts here; this exercise does not authenticate three independent people.

## 2:35–3:15: Apply the support amendment

**Action:** Close the panel and switch to **Analyst**. Open **Change review** and click **Apply AMD01**. In the newest change record, show P03 R03 changing from **Supported** to **Not satisfied**. Click **Inspect current evidence** and its source assertion to show 24 months. Close the panel and open **Decision package**. Show the first snapshot's **Stale** badge and **Previous review / approval is stale** message.

**Say:**

> AMD01 replaces the support commitment. P03 now has 24 months of support against a 36-month requirement. Its eligibility changes, and the earlier approval becomes stale. The original record remains available with its old sources. CEDAR conservatively invalidates every earlier snapshot whenever an input changes; it does not silently carry approval forward.

## 3:15–4:15: Record the unresolved decision honestly

**Action:** Still as Analyst, create a new P03 snapshot with **Conditional — record open blockers** and the conditional rationale below. Switch to Reviewer and record the conditional review note. Switch to Approver and approve with the conditional approval note. Close the panel. Show the new snapshot's conditional decision text beside its **Approved** status, with **Open mandatory gates** still visible. Click **Export decision ZIP** on this new snapshot.

**Say:**

> We can record a hold for clarification, but we cannot label P03 unconditionally eligible. This conditional record keeps the failed requirement visible. The new review and approval authorize the recorded hold only. The export includes the decision, alternatives, assumptions, outstanding questions, exact sources and verification instructions. No clarification question is sent to a supplier.

## 4:15–4:45: Show the portable result and its limit

**Action:** Open the exported ZIP with the archive viewer and show `report.html`, `decision.json`, `evidence.csv`, `manifest.json` and `VERIFY.txt`. Open the extracted `report.html` for an offline review. If running a verifier live, use the downloaded ZIP's actual path with the trusted repository command shown below.

**Say:**

> A reviewer can inspect this package without the running application. Hash checks detect inconsistency with the supplied manifest. They do not prove supplier truth, reviewer identity or approval currency after a future amendment. The next useful test is a bounded pilot with permitted documents and human annotations, measuring errors and total review effort. This demonstration has no customer validation or measured time-saving claim.

## Exact review text

| Field | Text to paste |
|---|---|
| First rationale | Retain P03 for documentary consideration under V1 and two replacement batteries per aircraft per year. All supplied evidence is synthetic; no purchase is authorized. |
| First technical review | Demonstration review: source references, documentary gates and recorded cost assumptions checked for this snapshot. |
| First approval | Approve further documentary consideration only. No purchase or field-performance certification is authorized. |
| Conditional rationale | Hold P03 pending a support commitment that meets the 36-month requirement. AMD01 reduced the documented commitment to 24 months. Open gates remain; compare eligible alternatives. |
| Conditional technical review | Reviewed the amended support passage and unresolved gate. This record preserves a hold for clarification. |
| Conditional approval | Approve the recorded hold for clarification only. P03 remains ineligible for an unconditional recommendation. |

## Reproducible replay and package verification

The full API walkthrough runs in a temporary database, checks that an analyst approval attempt returns HTTP 403, and repeats the same cost, amendment, stale-approval and conditional-export story:

```sh
uv run --frozen python -m cedar walkthrough
uv run --frozen python scripts/verify_package.py artifacts/full-decision.zip
```

Read `artifacts/walkthrough.json` for the recorded steps and `artifacts/full-stale-decision.zip` for the preserved earlier decision. These files come from the API replay, separately from the browser's downloaded ZIP. To verify the browser download, replace the example path with its actual location:

```sh
uv run --frozen python scripts/verify_package.py /path/to/downloaded-decision.zip
```

After extracting a trusted sample package, its portable verifier can also run without project dependencies:

```sh
python3 verify.py .
```

The complete verification entry point is `uv run --frozen python -m cedar verify`. The archive verifier checks content consistency and citation binding; it does not rerun the purchasing analysis. A verifier distributed inside an untrusted archive also needs a trusted source.

For questions after the main demonstration, open **Evidence viewer** to filter the ledger or **Software assurance** to inspect a component disposition and its procurement consequence. All advisory identifiers are synthetic. A declared component and a supplier exposure statement do not establish real exploitability.
