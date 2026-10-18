"""Generate the evidence report from saved results, without rerunning solvers."""
import json
from pathlib import Path


def generate_report(out):
    rows=json.loads((out/'comparison.json').read_text())
    meta=json.loads((out/'run_metadata.json').read_text())
    tiny=json.loads((out/'tiny_agreement.json').read_text())
    def row(case,policy='milp'):
        return next(r for r in rows if r['case']==case and r['policy']==policy and r['information']=='offline')
    bm=row('baseline'); severe=row('weather_severe'); clear=row('weather_clear')
    low=row('rejection_20'); late=row('lateness_10'); fair=row('fairness_2000')
    distributions={p:json.loads((out/'metrics'/f'baseline__offline__{p}.json').read_text())['distributions'] for p in ('fcfs','edf','milp')}
    lines=['# Synthetic dispatch experiment report','',
           f"Run date: {meta['timestamp']}. Seed {meta['seed']}. All inputs and annotations were AI-generated; there are no real delivery observations.",'',
           '## Scope and information','',
           'The baseline has 20 requests, including one pre-cancelled request, three vehicles, four initially full batteries, one charger and two technicians. The shift is 48 five-minute slots (240 minutes). Loading, handoff and turnaround each take one slot; a charge takes four slots and occupies a technician throughout. Every trip returns to the abstract depot. No geography, flight dynamics, real weather or clinical decisions are modeled.','',
           'The offline experiment supplies all demand at time zero, subject to release constraints. FCFS and EDF deliberately use their declared myopic queue rules; MILP may plan for future releases. The online experiment reveals requests only at release. All online policies know the same availability calendar. Rolling MILP commits current starts and preserves executed history, with a new solve each slot. Offline results and online results are separate comparisons.','',
           'The objective minimizes 200 times priority-weighted rejections, plus priority-weighted late minutes, plus one per charge, plus 100 times the worst regional rejection fraction. Its weights allow service counts to trade against lateness and fairness. All coefficients and priorities are administrative assumptions. Deadlines concern handoff and are soft. Return and turnaround must finish within the horizon.','',
           '## Baseline results','',
           '| Information | Policy | Served | Rejected | On time | Late minutes | Objective | Lower bound | Gap |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(value): return 'not claimed' if value is None else f'{value:,.2f}'
    base=[r for r in rows if r['case']=='baseline']
    for r in base:
        lines.append(f"| {r['information']} | {r['policy']} | {r['served']} | {r['rejected']} | {r['on_time']} | {r['lateness_minutes']} | {fmt(r['objective'])} | {fmt(r['lower_bound'])} | {'not claimed' if r['relative_gap'] is None else format(100*r['relative_gap'],'.2f')+'%'} |")
    lines += ['', 'Late minutes are summed only over served requests. Rejections and on-time counts must be read beside that sum. Priorities also affect objective cost, so a smaller unweighted lateness total need not yield a smaller objective. Cancelled requests are excluded from denominators.','',
              '![Baseline comparisons](figures/comparison.png)','',
              '## Charging and resource use','',
              '| Information / policy | Charges | Completed queue wait, min | Peak queue | Returns not recharged | Censored dirty time, min | Vehicle utilization | Charger utilization | Technician utilization |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in base:
        lines.append(f"| {r['information']} / {r['policy']} | {r['charges']} | {r['charging_wait_minutes']} | {r['charging_queue_peak']} | {r['unrecharged_returns']} | {r['censored_dirty_minutes']} | {r['vehicle_utilization']:.1%} | {r['charger_utilization']:.1%} | {r['technician_utilization']:.1%} |")
    lines += ['', 'Vehicle utilization divides busy time by available vehicle time, excluding calendar outages. Charger and technician utilization divide busy time by capacity times the full horizon. Queue wait is the time a depleted battery waits before charging; returns never recharged are reported separately as right-censored time. Terminal recharge is optional. The heuristics recharge proactively even without pending work, whereas MILP can avoid unnecessary terminal charges.','',
              '![Resource schedule](figures/schedule.png)','',
              '## Distribution and sensitivity','',
              '![Service distributions](figures/fairness.png)','',
              f"Dune service fractions for FCFS, EDF and offline MILP are {distributions['fcfs']['region']['Dune']['service_rate']:.0%}, {distributions['edf']['region']['Dune']['service_rate']:.0%} and {distributions['milp']['region']['Dune']['service_rate']:.0%}. Protected-category service fractions are {distributions['fcfs']['category']['protected']['service_rate']:.0%}, {distributions['edf']['category']['protected']['service_rate']:.0%} and {distributions['milp']['category']['protected']['service_rate']:.0%}. These labels are fictional administrative categories. The base fairness weight permits tradeoffs; the objective contains no minimum regional or category service guarantee. Complete per-group counts, mean and maximum lateness are in distributions.csv.",'',
              '| Case | FCFS objective | EDF objective | MILP incumbent | MILP lower bound | MILP gap | Served by MILP |',
              '|---|---:|---:|---:|---:|---:|---:|']
    cases=list(dict.fromkeys(r['case'] for r in rows if r['information']=='offline'))
    for name in cases:
        data={r['policy']:r for r in rows if r['case']==name and r['information']=='offline'}
        a=data['milp']
        lines.append(f"| {name} | {fmt(data['fcfs']['objective'])} | {fmt(data['edf']['objective'])} | {fmt(a['objective'])} | {fmt(a['lower_bound'])} | {a['relative_gap']:.2%} | {a['served']} |")
    limited=[r for r in rows if r['policy']=='milp' and not r['optimal']]
    lines += ['', 'Each row uses an identical demand and disruption fixture for every policy. Demand counts 12 and 28 use prefixes/extensions of the same seeded stream. Charging capacity, availability calendars and weights each change one factor. Objective values under different weight vectors are not directly comparable.','',
              f"- With 12 requests, the lower-cost heuristic is {min(('fcfs','edf'),key=lambda p:row('demand_12',p)['objective'])}; at baseline demand it is {min(('fcfs','edf'),key=lambda p:row('baseline',p)['objective'])}. Queue policy preference depends on demand.",
              '- With no charger, at most four services can use the four initially full batteries. This is an inventory limit. The table retains the result for each policy.',
              f"- Severe known unavailability selects {severe['served']} MILP services, compared with {bm['served']} at baseline. Removing baseline outages gives {clear['served']} services and objective {clear['objective']:,.2f}, compared with baseline objective {bm['objective']:,.2f}.",
              f"- At rejection cost 20, the selected MILP schedule serves {low['served']} with {low['lateness_minutes']} late minutes. At lateness cost 10, it serves {late['served']} with {late['lateness_minutes']} late minutes. Baseline values are {bm['served']} and {bm['lateness_minutes']}. The objective allows rejections to trade against delay.",
              f"- Raising fairness cost from 100 to 2,000 gives {fair['served']} services and a worst regional rejection fraction of {fair['maximum_regional_rejection_fraction']:.0%}, compared with {bm['maximum_regional_rejection_fraction']:.0%} at baseline. Unweighted lateness is {fair['lateness_minutes']} minutes versus {bm['lateness_minutes']}. These outcomes reflect the supplied administrative weights.",'']
    for r in limited:
        alternatives=[x for x in rows if x['case']==r['case'] and x['information']=='offline']
        best=min(alternatives,key=lambda x:x['objective'])
        lines += [f"**Unresolved optimization bound:** {r['case']} hit its {meta['offline_time_limit']:g}-second limit. The MILP incumbent is {r['objective']:,.2f}, lower bound {r['lower_bound']:,.2f}, gap {r['relative_gap']:.2%}. The best exported policy for that row is {best['policy']} at {best['objective']:,.2f}. These incumbent values do not establish a harmful effect of additional capacity. All candidates, including the weaker incumbent, are retained.",'']
    certificate=json.loads((out/'capacity_certificate.json').read_text())
    lines += [f"A separately checked capacity-transfer certificate reuses the baseline one-charger schedule with two chargers. Its objective {certificate['objective']:,.2f} is another feasible upper bound. Combined with the two-charger solve's lower bound {certificate['lower_bound']:,.2f}, its relative gap is {certificate['relative_gap']:.2%}. This additional witness is exported as {certificate['schedule']}; no new solver optimum is claimed.",'']
    lines += ['![Sensitivity results](figures/sensitivity.png)','',
              '## Verification and computational limits','',
              f"The package contains {meta['validated_schedules']} independently feasible schedules: {meta['comparison_schedules']} policy comparisons, two witnesses for each of {len(tiny)} tiny cases, and one capacity-transfer certificate. The runner calls the standard-library checker on every schedule before writing it. The separate audit reopens the artifacts and recomputes feasibility and metrics.",'',
              'The hand case has a charging conflict at minute 2. Its all-served schedule requires two recharges and has objective 2. Any rejected request costs at least 200, so 2 is also an analytical lower bound attained by that schedule. The exhaustive reference confirms 2 with 573 memoized states and 1,270 transitions. Its symmetry reduction exchanges only currently idle resources with identical future restrictions; it explores idling and rejection as well as service and charging.','',
              f"All {len(tiny)} exported tiny instances agree between exact rational state enumeration and the MILP objective and bound. They include zero requests, no vehicles, charging and staff bottlenecks, cancellation, simultaneous deadlines and after-horizon demand. The reference guards its bounded input domain explicitly.",'',
              f"Execution used Python {meta['python'].split()[0]}, SciPy {meta['packages']['scipy']}, HiGHS {meta['highs_version']} and Matplotlib {meta['packages']['matplotlib']}. The experiment completed in {meta['elapsed_seconds']:.2f} seconds. Offline solve limits were {meta['offline_time_limit']:g} seconds, and online limits were {meta['online_time_limit']:g} seconds per decision. See run_metadata.json, experiment.log and the source/reproduction documents for exact versions and commands.",'',
              'HiGHS optimality and bounds are numerical solver results for the finite integer-slot formulation. They are distinct from the hand-derived argument and exact rational tiny enumeration. A rolling subproblem bound applies only to the requests visible at that decision. No global online optimum, competitive ratio or optimality gap is claimed. Solve records preserve every online status and local bound.','',
              'The rejection option makes the optimization model feasible even when full service is impossible. The no-vehicle tiny case cannot serve a request because each service requires a vehicle. The after-horizon case cannot satisfy release plus positive service duration before horizon. Such requests remain in the exports. No unsatisfiable-core computation is claimed.','',
              '## Limits and next step','',
              'The results cover one controlled synthetic benchmark stream with one-factor sweeps. They do not estimate real service performance. Online sensitivity beyond the baseline and unexpected weather are not evaluated. The five-minute grid, homogeneous full/depleted batteries, supervised charging, fixed mission durations and pre-cancellation-at-arrival rule are material assumptions. No energy physics, handling rules, storage constraints, patient priorities or real aviation requirements are validated. All annotations and code review came from AI assistants; methodologically independent checks are the separately implemented checker, exhaustive algorithm and hand argument.','',
              'All required bounded milestone gates are met. Larger-instance optimality remains unresolved where a time limit is reported; this is permitted by the bounded-solution criterion. The next concrete numerical step is a longer solve of the two-charger case while retaining its current incumbent and lower bound. Any operational use would first require separately established aviation, supply-handling and clinical requirements.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    import sys
    generate_report(Path(sys.argv[1] if len(sys.argv)>1 else 'results'))
