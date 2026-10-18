# Dispatch model, assumptions, and evidence scope

Each request asks for one indivisible delivery from Depot to a fictional region and back. A service needs one vehicle, one full battery, and one technician for loading. A charge needs one depleted battery, one charger, and one technician for its entire duration. The objective combines rejection, late handoff, charging, and regional rejection fractions.

This document describes [optimize.py](../dispatch/optimize.py), [simulate.py](../dispatch/simulate.py), and the interchange semantics in [contract.md](contract.md). API references, access dates, package versions, and the online documentation version caveat are recorded in [sources.md](sources.md). The optimization uses SciPy milp and its HiGHS backend. The referenced OR-Tools material is background; this implementation does not run CP-SAT.

## Units and timing

Let the horizon be \(H\) integer slots and each slot represent \(\Delta\) minutes. Permitted operation starts are integer boundaries \(0,\ldots,H-1\); every operation finishes by boundary \(H\). Integer travel and service durations are inputs. The code does not round a continuous-time schedule or establish that an integer-slot optimum is optimal among continuous-time schedules.

For request \(r\), write \(a_r\) for release, \(d_r\) for deadline, \(p_r>0\) for its administrative priority multiplier, and \(g_r\) for region. Let \(\ell>0\) be loading duration, \(h\geq0\) handoff duration, \(b\geq0\) turnaround duration, and \(q>0\) charge duration. Let \(T_{ij}\) be the directed abstract travel-time matrix.

The handoff and return offsets are

\[
\delta_r=\ell+T_{\mathrm{Depot},g_r}+h,\qquad
L_r=\delta_r+T_{g_r,\mathrm{Depot}}+b.
\]

A service starting at \(s\) delivers at \(s+\delta_r\) and returns its vehicle and battery at \(s+L_r\). Its vehicle and battery are occupied on \([s,s+L_r)\); its loading technician is occupied on \([s,s+\ell)\). The battery becomes depleted at return, so it cannot be charged during the mission. A charge starting at \(c\) occupies its battery, charger, and technician on \([c,c+q)\), and produces a full battery at \(c+q\).

All intervals are half open. Returns, loading completions, and charge completions at a boundary precede new acquisitions at that boundary. The deadline is a soft target for completed handoff. Return and turnaround need only fit the horizon. Late minutes for a selected start are

\[
\lambda_{rs}=\Delta\max(0,s+\delta_r-d_r).
\]

## Scenario and output dictionary

| Input field | Meaning and unit |
| --- | --- |
| id, seed | Scenario identifier and deterministic synthetic-generator seed. The generator seed records provenance. |
| horizon | Positive integer number of slots \(H\). |
| slot_minutes | Positive integer minutes per slot \(\Delta\). |
| load_time | Positive integer loading duration \(\ell\), in slots. |
| handoff_time, turnaround_time | Nonnegative integer durations \(h,b\), in slots. |
| charge_duration | Positive integer duration \(q\), common to every recharge. |
| vehicles | Named vehicles, each with unavailable intervals [start,end] in slots. Complete service intervals must avoid these intervals. |
| battery_ids | Named homogeneous batteries, all full at time zero. Each mission consumes one charge. |
| charger_ids | Named homogeneous chargers. Each handles at most one charge at a time. |
| technician_ids | Named homogeneous technicians. Each handles one loading task or supervises one charge at a time. |
| travel | Nested matrix of nonnegative integer durations including Depot and request regions. Only Depot-to-region and region-to-Depot entries affect a mission. |
| requests[].id | Unique request identifier. |
| requests[].release | Nonnegative earliest loading-start slot \(a_r\). |
| requests[].deadline | Nonnegative target handoff slot \(d_r\); no hard deadline rejection rule is applied. |
| requests[].region, category | Fictional reporting groups. Region also selects travel durations and the fairness cohort. |
| requests[].priority | Positive integer administrative multiplier \(p_r\), used for rejection and lateness costs. |
| requests[].cancelled | Boolean administrative pre-dispatch cancellation, revealed with the request. |
| weights.rejection | Nonnegative illustrative cost per rejected priority unit. |
| weights.lateness | Nonnegative illustrative cost per priority-weighted late minute. |
| weights.charge | Nonnegative illustrative cost per charge started. |
| weights.fairness | Nonnegative illustrative cost per unit of the worst regional rejection fraction. |

Empty resource lists and empty demand are valid stress cases. They may force rejection without making the scheduling model infeasible, because accepting a request is optional.

| Output field | Interpretation |
| --- | --- |
| scenario_id, policy, information | Scenario identity, policy name, and declared offline or online information regime. |
| services | Request, vehicle, battery, and loading-technician IDs, plus integer start, delivery, and end boundaries. |
| charges | Battery, charger, and supervising-technician IDs, plus integer start and end boundaries. |
| unserved | Exactly one record for each request without service; status distinguishes cancelled from rejected, with a reason. |
| decisions | Heuristic and rolling-policy logs with time, visible request IDs, and irrevocably executed service and charge starts. |
| solver | Method-specific status, elapsed time, objective and bound information where available. Status metadata does not replace schedule checking. |

Every request appears in exactly one service or unserved record. Cancellations consume no resource and enter no eligible-service denominator. An unserved noncancelled request can reflect either unavailable resources or an objective-driven decision to reject; the optimizer does not claim that every rejection was unavoidable.

## Integer-slot MILP

The formulation below is the offline problem. A later section gives the exact restrictions used for online replanning.

Let \(R\) contain noncancelled requests, \(V\) the vehicles, and \(B,C,K\) the counts of batteries, chargers, and technicians. Let \(\mathcal U_v\) contain vehicle \(v\)'s unavailable intervals. Define the feasible service candidates

\[
\mathcal A=\{(r,v,s):r\in R,\ v\in V,\ s\in\mathbb Z,\ 
a_r\le s,\ s+L_r\le H,\ 
[s,s+L_r)\cap[u,w)=\varnothing\ \forall[u,w)\in\mathcal U_v\}.
\]

Each candidate has a binary variable \(x_{rvs}\). A value of one selects that request, vehicle, and loading start. Let \(k_c\) be the integer count of charges started at boundary \(c\), for \(c\in\mathcal C=\{0,\ldots,H-q\}\), with \(\mathcal C=\varnothing\) if \(q>H\). Finally let \(z\in[0,1]\) represent the worst regional rejection fraction.

\[
x_{rvs}\in\{0,1\},\qquad k_c\in\{0,\ldots,C\},\qquad 0\le z\le1.
\]

Define \(y_r=\sum_{(r,v,s)\in\mathcal A}x_{rvs}\). The constraints are:

1. **At most one service per eligible request**

   \[
   0\le y_r\le1\qquad(r\in R).
   \]

   A request with no candidate has \(y_r=0\).

2. **Vehicle occupancy**, for every vehicle \(v\) and slot \(t=0,\ldots,H-1\):

   \[
   \sum_{\substack{(r,v,s)\in\mathcal A\\s\le t<s+L_r}}x_{rvs}\le1.
   \]

   Availability is already enforced when candidates are created.

3. **Charger occupancy**, for every slot \(t\):

   \[
   \sum_{\substack{c\in\mathcal C\\c\le t<c+q}}k_c\le C.
   \]

4. **Shared technician occupancy**, for every slot \(t\):

   \[
   \sum_{\substack{(r,v,s)\in\mathcal A\\s\le t<s+\ell}}x_{rvs}
   +\sum_{\substack{c\in\mathcal C\\c\le t<c+q}}k_c\le K.
   \]

   Charging supervision lasts for the whole charge, while loading supervision ends before travel.

5. **Full-battery inventory**, for every boundary \(t=0,\ldots,H-1\):

   \[
   \sum_{\substack{(r,v,s)\in\mathcal A\\s\le t}}x_{rvs}
   -\sum_{\substack{c\in\mathcal C\\c+q\le t}}k_c\le B.
   \]

   Cumulative mission starts cannot exceed initial full stock plus completed charges. A charge ending at \(t\) can supply a mission starting at \(t\).

6. **Depleted-battery inventory**, for every boundary \(t\):

   \[
   \sum_{\substack{c\in\mathcal C\\c\le t}}k_c
   -\sum_{\substack{(r,v,s)\in\mathcal A\\s+L_r\le t}}x_{rvs}\le0.
   \]

   Cumulative charge starts cannot exceed completed missions. A battery returning at \(t\) can begin charging at \(t\). No initially full battery can be charged before it has completed a mission.

7. **Regional rejection fraction.** For each region with a nonempty eligible cohort \(R_g=\{r\in R:g_r=g\}\):

   \[
   z+\frac{1}{|R_g|}\sum_{r\in R_g}y_r\ge1.
   \]

   These fractions count requests equally; priority does not weight the fairness denominator. Empty cohorts are omitted.

With weights \(w_R,w_L,w_C,w_F\), the reported objective is

\[
J=
w_R\sum_{r\in R}p_r(1-y_r)
+w_L\sum_{(r,v,s)\in\mathcal A}p_r\lambda_{rs}x_{rvs}
+w_C\sum_{c\in\mathcal C}k_c
+w_F\max_{g:|R_g|>0}\left(1-\frac{\sum_{r\in R_g}y_r}{|R_g|}\right).
\]

The maximum over no eligible regions is defined to be zero. The MILP substitutes \(z\) for that maximum. If \(w_F>0\), minimization makes \(z\) tight. If \(w_F=0\), a non-tight \(z\) leaves the objective unchanged. Reported metrics recompute the actual regional maximum from the schedule.

No constraint requires service of every request, on-time handoff, or recharging all batteries before \(H\). Rejection always supplies a feasible empty schedule in the offline problem, including zero-resource cases. A rolling subproblem retains the feasibility of a valid committed prefix by accepting no further requests or charges.

### Why aggregate battery counts reconstruct named resources

The model does not assign a battery, charger, or technician to each decision variable. Their identity is reconstructed by forward replay in the optimizer's materialization function.

An induction over integer boundaries explains why this is sufficient for the stated homogeneous-resource model. Initially, the \(B\) named batteries are full and idle. At each boundary, first return every completed mission's battery to the depleted pool, and return every completed charge's battery to the full pool. Also release chargers and technicians whose loading or charge supervision has ended.

The full-battery inequality guarantees enough members in the full pool for all mission starts at that boundary. Assign one distinct available member to each mission and remove it from the pool. The depleted-battery inequality guarantees enough members in the depleted pool for all charge starts. Assign and remove one distinct member per charge. Full and depleted pools are disjoint, so a charge and a mission cannot consume the same battery. Positive operation durations prevent a newly started operation from completing within the same boundary.

More explicitly, after acquisitions at \(t\),

\[
F_t=B+\sum_{c+q\le t}k_c-\sum_{s\le t}x_{rvs},\qquad
D_t=\sum_{s+L_r\le t}x_{rvs}-\sum_{c\le t}k_c.
\]

The service sums range over \(\mathcal A\), and charge sums over \(\mathcal C\). The inventory constraints give \(F_t,D_t\ge0\). With \(M_t\) active missions and \(Q_t\) active charges, the same cumulative differences give

\[
F_t+D_t+M_t+Q_t=B.
\]

Thus battery identities are conserved across idle, mission, and charging states. Charger and technician occupancy inequalities give enough idle named resources for the starts at each boundary. The replay assigns the first available IDs, with depleted batteries ordered by return time and then ID. Vehicles retain the identities already chosen by the MILP, because their availability calendars can differ.

This argument depends on identical battery capacities and charge durations, interchangeable chargers, and technicians without individual calendars or skills. Introducing resource-specific compatibility or durations would require additional constraints. The independent checker verifies the reconstructed named schedule directly; it does not rely on this reconstruction code or on solver status.

### Shifted objective, status, and bounds

The SciPy objective omits the constant

\[
C_0=w_R\sum_{r\in R}p_r.
\]

Each service coefficient is \(p_r(w_L\lambda_{rs}-w_R)\); each charge coefficient is \(w_C\); the \(z\) coefficient is \(w_F\). Consequently the raw solver objective and dual bound concern \(J-C_0\), which may be negative.

The implementation adds \(C_0\) to the dual bound before reporting it against the full schedule objective. It clips that translated lower bound below at zero because every original objective term is nonnegative. When no finite solver bound is available, it reports the valid trivial lower bound zero. The reported relative gap is

\[
\frac{\max(0,J-\mathrm{lower\_bound})}{\max(|J|,10^{-12})}.
\]

The raw_mip_gap field is preserved separately. It refers to the solver's shifted objective, so it can differ from the reported translated gap. Comparing gaps without accounting for the constant can misstate how much uncertainty remains in the full objective.

Each solve records its status code, solver message, requested time limit, elapsed time, incumbent objective, bound, variable and constraint counts, and node count when available. The optimal field is true only for status zero with an incumbent. A time limit with an incumbent reports that feasible result and its available bound. A solve with no incumbent returns the committed prefix, or an empty schedule offline, marks used_fallback, and makes no optimality claim. The implementation checks integrality to tolerance and checks the translated incumbent objective against recomputed schedule metrics. These numerical checks provide no formal-proof certificate.

## Information regimes and policy rules

| Policy | Demand used for decisions | Dispatch and charging behavior |
| --- | --- | --- |
| Offline FCFS | Released requests only, although the environment has the full input | Sort pending requests by (release, id); scan for currently feasible starts. |
| Offline EDF | Released requests only, although the environment has the full input | Sort pending requests by (deadline, release, id); scan for currently feasible starts. |
| Offline MILP | Every input request, including future releases | Jointly choose service starts and charges over the horizon under the full objective. |
| Online FCFS and EDF | Requests revealed through arrival events | Use the same dispatch and charging rules as their offline-labelled versions. |
| Online rolling MILP | Only requests with release at or before current time | Re-solve the known-request problem at each integer boundary and execute only starts at that boundary. |

The offline comparison uses the same known-demand environment for all methods. Its heuristics deliberately ignore advance demand, so differences from offline MILP include both dispatch quality and the value of planning future arrivals. The online comparison gives every policy the same request revelations and the same availability calendar.

Both heuristics bypass an infeasible queue head. Resource assignments use sorted IDs. Services acquire resources before charges at the same decision time. They then start FIFO charges for depleted batteries whenever a charger and technician are free and completion fits the horizon. This proactive rule applies even with no pending request and uses no future-demand forecast. It can create an unnecessary terminal charge. The optimizer has no terminal recharge obligation and can omit that charge when it has positive cost.

Online cancellation is visible only when its request arrives. There is no cancellation after service starts. Final reporting can classify every input request, including one released after the horizon, after all actions are fixed; those classifications are not inputs to earlier decisions.

At rolling decision boundary \(\tau\), the optimizer receives a projected scenario containing only revealed requests. Already executed starts strictly before \(\tau\) form the prefix. Their chosen request, vehicle, and start are fixed; counts of charge starts before \(\tau\) are fixed as well. Uncommitted service candidates start at or after \(\max(\tau,a_r)\). Future charge starts and future services can be revised until executed. In-progress intervals remain in the capacity and inventory constraints.

Forward reconstruction explicitly reuses battery, charger, and technician IDs from the validated prefix. New actions use deterministic resource assignment. Each projected problem uses the known requests, including earlier served requests, for its regional cohort denominators. Later arrivals can change those denominators.

The rolling policy has no arrival forecast. It may omit charging while no known request needs energy, then wait for a recharge after an unexpected arrival. The heuristic's proactive charging can behave differently. Each rolling solve's bound concerns only its current known-request integer-slot problem with its fixed prefix. It is not a lower bound or optimality certificate for the complete online policy across future arrivals. The exported rolling result therefore has no global bound or relative gap.

## Assumption register

| Assumption | Consequence and limitation |
| --- | --- |
| All demand, institutions, regions, priorities, and availability intervals are synthetic administrative inputs | There is no patient data, clinical urgency inference, qualified operational review, or claim of medical suitability. |
| Every trip starts and ends at Depot | Inter-region travel entries do not influence decisions. No route or geographic path is generated. |
| Directed travel need not be symmetric or satisfy triangle inequalities | Only the supplied outward and return durations are used. Zero off-diagonal times are limited to abstract reference fixtures. |
| Operations are indivisible and deterministic | No preemption, batching, failed mission, uncertain duration, or mid-mission cancellation is modeled. |
| One full battery powers any one mission | There is no range, payload, energy curve, reserve, battery aging, or duration-dependent consumption model. |
| All batteries start full; a mission releases its battery depleted | A battery cannot charge while away, and no partial-charge state exists. |
| Technician capacity covers loading and whole-charge supervision | Travel requires no technician; one technician cannot load and supervise charging simultaneously. |
| Availability calendars are known at time zero | Weather sensitivity means synthetic changes to calendar blocks, with no weather observations or forecast model. |
| Entire vehicle occupancy must avoid unavailability | Loading, handoff, return, and turnaround are all included in the calendar check. |
| Deadline is a soft handoff target; every operation finishes by the horizon | Late service is permitted, but an early handoff with return after the horizon is forbidden. |
| Rejection is permitted and every cost weight is nonnegative | Feasible service can be rejected when its objective cost is higher. Zero weights can produce multiple equally optimal schedules. |
| Regional fairness is the worst unweighted rejection fraction | It does not directly constrain regional lateness, category fairness, individual outcomes, or priority-weighted acceptance. Category outcomes are reported separately. |
| There is no mandatory terminal recharge | A depleted battery at the horizon is feasible. A heuristic recharge can increase cost without increasing completed service. |
| Scheduling is limited to the chosen slot grid | Bounds and exact tiny-case comparisons apply to that discretization and the declared horizon. |

The objective measures illustrative administrative cost units. No clinical or monetary valuation is estimated. A lower aggregate objective can coexist with worse service or lateness in one group. Region and category distributions must therefore be read alongside aggregate comparisons.

## Metrics and evidence classes

The metrics module recomputes outcomes from exported operations. Total lateness is in minutes; objective lateness also applies the request priority multiplier. Vehicle utilization divides occupied slots by available vehicle slots after calendar exclusions. Charger and technician utilization use their resource counts times the horizon. Reported zero-capacity utilization is zero by convention.

Charging wait starts at depleted battery return and ends at its next charge start. Completed waits and their maximum exclude batteries never recharged. Those depleted intervals are right-censored at the horizon and reported separately as unrecharged_returns and censored_dirty_minutes; a zero completed-wait total does not show that every battery was recharged. Queue peaks count depleted batteries waiting, including censored intervals, and exclude active charges.

The project distinguishes three kinds of evidence:

1. **Analytical hand-fixture argument.** Four missions use four full charges of energy and only two batteries begin full, so any all-served schedule needs at least two recharge operations. The contract's hand schedule attains two charges, zero rejection, and zero lateness, with objective two. Every schedule with a rejection costs at least 200 under that fixture's weights. This gives a global optimum of two for that fixture. The proactive heuristics' extra terminal charge does not invalidate the optimum; it shows a declared policy choice can be suboptimal.
2. **Bounded exhaustive reference.** The reference implementation enumerates integer-slot action sets, including idling and rejection, for at most four requests, horizon at most eight, and at most two resources of each type. It uses exact rational objective comparisons and memoized states after valid resource-symmetry reductions. Reported state counts are not counts of every labeled schedule. Explicit state and transition guards raise an error rather than return a truncated search as exact. An optimum from a completed enumeration applies only to its supplied bounded instance and assumptions.
3. **Numerical MILP results.** HiGHS status and translated dual bounds describe the solved integer-slot model within solver tolerances and the requested compute limit. A feasible incumbent is checked independently. Matching a tiny exhaustive optimum tests implementation consistency; it does not prove every larger instance solved, or establish operational validity.

The independent checker reconstructs request coverage, timing, availability, battery transitions, and named vehicle, charger, and technician overlaps without importing simulator or optimizer internals. Checker acceptance supports feasibility under the contract. Benchmark values, completed verification counts, sensitivity outcomes, and actual solver termination records belong in generated results and the execution report, rather than being inferred from this formulation.
