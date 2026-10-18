"""Time-indexed MILP and nonanticipating rolling-horizon policy."""
import copy
import math
import time
from collections import Counter
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from .schema import durations, validate_scenario
from .metrics import summarize
from .checker import validate_schedule


def _materialize(s, chosen, charge_counts, policy='milp', information='offline', prefix=None):
    """Assign resource identities by forward replay of aggregate integer decisions."""
    full = set(s['battery_ids'])
    dirty = {}
    tech_until = {x: 0 for x in s['technician_ids']}
    charger_until = {x: 0 for x in s['charger_ids']}
    services, charges = [], []
    requests = {r['id']: r for r in s['requests']}
    prefix = prefix or {'services': [], 'charges': []}
    fixed_services = {a['request_id']: a for a in prefix['services']}
    for t in range(s['horizon']+1):
        for a in services:
            if a['end'] == t:
                dirty[a['battery_id']] = t
        for c in charges:
            if c['end'] == t:
                full.add(c['battery_id'])
        # Identity choices depend only on past and current actions.
        for rid, vid, start, delivery, end in sorted(chosen):
            if start != t:
                continue
            past = fixed_services.get(rid)
            bid = past['battery_id'] if past else min(full)
            full.remove(bid)
            tid = past['technician_id'] if past else min(x for x,v in tech_until.items() if v <= t)
            tech_until[tid] = t+s['load_time']
            services.append(dict(request_id=rid, vehicle_id=vid, battery_id=bid,
                                 technician_id=tid, start=t, delivery=delivery, end=end))
        past_charges = sorted([c for c in prefix['charges'] if c['start']==t],key=lambda c:c['battery_id'])
        for number in range(charge_counts.get(t, 0)):
            past = past_charges[number] if number < len(past_charges) else None
            bid = past['battery_id'] if past else min(dirty, key=lambda b: (dirty[b], b))
            del dirty[bid]
            cid = past['charger_id'] if past else min(x for x,v in charger_until.items() if v <= t)
            tid = past['technician_id'] if past else min(x for x,v in tech_until.items() if v <= t)
            end = t+s['charge_duration']
            charger_until[cid] = tech_until[tid] = end
            charges.append(dict(battery_id=bid, charger_id=cid, technician_id=tid, start=t, end=end))
    done = {a['request_id'] for a in services}
    unserved = [dict(request_id=r['id'], status='cancelled' if r['cancelled'] else 'rejected',
                     reason='cancelled_on_arrival' if r['cancelled'] else 'not_selected_under_resources_horizon_and_objective')
                for r in requests.values() if r['id'] not in done]
    return dict(scenario_id=s['id'], policy=policy, information=information,
                services=services, charges=charges, unserved=unserved, solver={})


def optimize(s, time_limit=3.0, now=0, prefix=None):
    """Optimize known requests. Prefix starts strictly before now are fixed."""
    validate_scenario(s)
    if type(now) is not int or not 0 <= now <= s['horizon']:
        raise ValueError('now must be an integer within the horizon')
    if time_limit < 0 or not math.isfinite(time_limit):
        raise ValueError('time_limit must be finite and nonnegative')
    h, q = s['horizon'], s['charge_duration']
    prefix = prefix or {'services': [], 'charges': []}
    if prefix['services'] or prefix['charges']:
        done = {a['request_id'] for a in prefix['services']}
        probe = dict(scenario_id=s['id'],policy='prefix',information='offline',solver={},**prefix,
                     unserved=[dict(request_id=r['id'],status='cancelled' if r['cancelled'] else 'rejected',reason='prefix validation')
                               for r in s['requests'] if r['id'] not in done])
        errors = validate_schedule(s,probe)
        if errors:
            raise ValueError(f'invalid fixed prefix: {errors}')
    fixed = {a['request_id']: a for a in prefix['services']}
    prior_charges = Counter(c['start'] for c in prefix['charges'])
    if any(a['start'] >= now for a in prefix['services'] + prefix['charges']):
        raise ValueError('prefix may contain only starts strictly before now')
    eligible = [r for r in s['requests'] if not r['cancelled']]
    req_index, vehicle_index = {}, {}
    candidates, costs, upper, integral = [], [], [], []
    w = s['weights']
    for r in eligible:
        req_index[r['id']] = []
        d,e = durations(s,r)
        for v in sorted(s['vehicles'], key=lambda x:x['id']):
            times = [fixed[r['id']]['start']] if r['id'] in fixed else range(max(now,r['release']), h-e+1)
            for t in times:
                if r['id'] in fixed and v['id'] != fixed[r['id']]['vehicle_id']:
                    continue
                if t < r['release'] or t+e > h or any(t < b and a < t+e for a,b in v['unavailable']):
                    continue
                j = len(costs)
                candidates.append((r['id'],v['id'],t,t+d,t+e))
                req_index[r['id']].append(j)
                vehicle_index.setdefault(v['id'], []).append(j)
                costs.append(r['priority']*(w['lateness']*max(0,t+d-r['deadline'])*s['slot_minutes']-w['rejection']))
                upper.append(1)
                integral.append(1)
    charge_index = {}
    for t in range(max(0,h-q+1)):
        charge_index[t] = len(costs)
        costs.append(w['charge'])
        upper.append(len(s['charger_ids']))
        integral.append(1)
    z = len(costs)
    costs.append(w['fairness'])
    upper.append(1)
    integral.append(0)
    rows, cols, vals, lb, ub = [], [], [], [], []
    def constraint(terms, low=-np.inf, high=np.inf):
        row = len(lb)
        for col, val in terms:
            rows.append(row); cols.append(col); vals.append(val)
        lb.append(low); ub.append(high)
    for rid, ix in req_index.items():
        constraint([(j,1) for j in ix], 1 if rid in fixed else 0, 1)
    for t,j in charge_index.items():
        if t < now:
            constraint([(j,1)],prior_charges[t],prior_charges[t])
    for t in range(h):
        for vid, ix in vehicle_index.items():
            constraint([(j,1) for j in ix if candidates[j][2] <= t < candidates[j][4]], high=1)
        charging = [(j,1) for c,j in charge_index.items() if c <= t < c+q]
        constraint(charging, high=len(s['charger_ids']))
        loading = [(j,1) for j,a in enumerate(candidates) if a[2] <= t < a[2]+s['load_time']]
        constraint(loading+charging, high=len(s['technician_ids']))
        # Full batteries: launches cannot exceed initial full stock plus completed recharges.
        constraint([(j,1) for j,a in enumerate(candidates) if a[2] <= t] +
                   [(j,-1) for c,j in charge_index.items() if c+q <= t], high=len(s['battery_ids']))
        # Dirty batteries: charge starts require an earlier or simultaneous completed service.
        constraint([(j,1) for c,j in charge_index.items() if c <= t] +
                   [(j,-1) for j,a in enumerate(candidates) if a[4] <= t], high=0)
    groups = {}
    for r in eligible:
        groups.setdefault(r['region'], []).append(r['id'])
    for region, ids in groups.items():
        constraint([(z,1)]+[(j,1/len(ids)) for rid in ids for j in req_index[rid]], low=1)
    matrix = coo_matrix((vals,(rows,cols)),shape=(len(lb),len(costs))).tocsc()
    constant = w['rejection']*sum(r['priority'] for r in eligible)
    begin = time.monotonic()
    res = milp(np.asarray(costs), integrality=np.asarray(integral),
               bounds=Bounds(np.zeros(len(costs)),np.asarray(upper)),
               constraints=LinearConstraint(matrix,np.asarray(lb),np.asarray(ub)),
               options={'time_limit': float(time_limit), 'mip_rel_gap': 0.0, 'presolve':True})
    elapsed = time.monotonic()-begin
    fallback = res.x is None
    if not fallback:
        if any(abs(res.x[j]-round(res.x[j])) > 1e-5 for j in range(z)):
            raise RuntimeError('solver returned a nonintegral incumbent')
        chosen = [a for j,a in enumerate(candidates) if res.x[j] > .5]
        counts = {t:int(round(res.x[j])) for t,j in charge_index.items()}
    else:
        chosen = [(a['request_id'],a['vehicle_id'],a['start'],a['delivery'],a['end']) for a in prefix['services']]
        counts = prior_charges
    schedule = _materialize(s,chosen,counts,prefix=prefix)
    value = summarize(s,schedule)['objective']
    dual = getattr(res,'mip_dual_bound',None)
    lower = float(dual)+constant if dual is not None and math.isfinite(dual) else None
    # Nonnegative objective gives a safe trivial bound when HiGHS reports none.
    lower = max(0.0, lower) if lower is not None else 0.0
    gap = max(0.0,value-lower)/max(abs(value),1e-12)
    if not fallback and abs((float(res.fun)+constant)-value) > 1e-4:
        raise RuntimeError('recomputed objective differs from solver objective')
    schedule['solver'] = dict(engine='SciPy milp / HiGHS',status=int(res.status),message=res.message,
                              optimal=res.status == 0 and not fallback,used_fallback=fallback,
                              feasible_objective=value,lower_bound=lower,relative_gap=gap,
                              raw_mip_gap=float(res.mip_gap) if getattr(res,'mip_gap',None) is not None else None,
                              objective_constant=constant,time_limit_seconds=time_limit,
                              elapsed_seconds=elapsed,nodes=int(res.mip_node_count) if getattr(res,'mip_node_count',None) is not None else None,
                              variables=len(costs),constraints=len(lb),bound_scope='known_request_integer_slot_problem')
    return schedule


def online_optimize(s, time_limit=.5):
    """Reveal at arrivals and replan each integer decision event; commit current starts only."""
    validate_scenario(s)
    prefix = dict(services=[], charges=[])
    decisions, solves = [], []
    # The environment reveals arrivals. Only the projected scenario enters optimize().
    for t in range(s['horizon']):
        visible = [r for r in s['requests'] if r['release'] <= t]
        snapshot = {k:copy.deepcopy(v) for k,v in s.items() if k != 'requests'}
        snapshot['requests'] = copy.deepcopy(visible)
        planned = optimize(snapshot,time_limit=time_limit,now=t,prefix=prefix)
        services = [a for a in planned['services'] if a['start'] == t]
        charges = [a for a in planned['charges'] if a['start'] == t]
        prefix['services'].extend(services)
        prefix['charges'].extend(charges)
        decisions.append(dict(time=t,visible_request_ids=sorted(r['id'] for r in visible),
                              service_starts=services,charge_starts=charges))
        solves.append(dict(time=t,**planned['solver']))
    done = {a['request_id'] for a in prefix['services']}
    result = dict(scenario_id=s['id'],policy='rolling_milp',information='online',**prefix,
                  unserved=[dict(request_id=r['id'],status='cancelled' if r['cancelled'] else 'rejected',
                                 reason='cancelled_on_arrival' if r['cancelled'] else 'unserved_at_horizon')
                            for r in s['requests'] if r['id'] not in done],decisions=decisions,
                  solver=dict(engine='rolling SciPy milp / HiGHS',optimal=False,lower_bound=None,
                              relative_gap=None,bound_scope='no_global_online_optimality_claim',
                              solve_records=solves,time_limit_per_decision_seconds=time_limit))
    return result
