"""Compute transparent outcomes from schedules, without solver state."""
from collections import defaultdict


def summarize(s, schedule):
    eligible = {r['id']: r for r in s['requests'] if not r['cancelled']}
    served = {a['request_id']: a for a in schedule['services']}
    rejected = [r for rid, r in eligible.items() if rid not in served]
    late = {rid: max(0, a['delivery'] - eligible[rid]['deadline']) * s['slot_minutes']
            for rid, a in served.items()}
    distributions = {}
    for dimension in ('region', 'category'):
        groups = defaultdict(list)
        for r in eligible.values():
            groups[r[dimension]].append(r)
        distributions[dimension] = {}
        for name, rs in sorted(groups.items()):
            done = [r for r in rs if r['id'] in served]
            values = [late[r['id']] for r in done]
            distributions[dimension][name] = dict(
                eligible=len(rs), served=len(done), rejected=len(rs)-len(done),
                service_rate=len(done)/len(rs),
                on_time=sum(late[r['id']] == 0 for r in done),
                mean_lateness_minutes=sum(values)/len(values) if values else None,
                max_lateness_minutes=max(values, default=None))
    max_fraction = max((1-g['service_rate'] for g in distributions['region'].values()), default=0)
    w = s['weights']
    components = dict(
        rejection=w['rejection']*sum(r['priority'] for r in rejected),
        lateness=w['lateness']*sum(eligible[rid]['priority']*v for rid,v in late.items()),
        charging=w['charge']*len(schedule['charges']), fairness=w['fairness']*max_fraction)
    # Reconstruct each dirty interval, including batteries not subsequently charged.
    dirty_events = []
    for a in schedule['services']:
        charges = [c for c in schedule['charges'] if c['battery_id'] == a['battery_id'] and c['start'] >= a['end']]
        next_c = min(charges, key=lambda c: c['start']) if charges else None
        dirty_events.append((a['end'], next_c['start'] if next_c else s['horizon'], bool(next_c)))
    waits = [(b-a)*s['slot_minutes'] for a,b,complete in dirty_events if complete]
    queue_peak = max((sum(a <= t < b for a,b,_ in dirty_events) for t in range(s['horizon'])), default=0)
    vehicle_busy = sum(a['end']-a['start'] for a in schedule['services'])
    available_vehicle_slots = sum(sum(not any(a <= t < b for a,b in v['unavailable'])
                                      for t in range(s['horizon'])) for v in s['vehicles'])
    technician_busy = len(served)*s['load_time'] + len(schedule['charges'])*s['charge_duration']
    def ratio(a,b):
        return a/b if b else 0.0
    return dict(scenario_id=s['id'], policy=schedule['policy'], information=schedule['information'],
                requests=len(s['requests']), eligible=len(eligible), served=len(served),
                rejected=len(rejected), cancelled=len(s['requests'])-len(eligible),
                on_time=sum(v == 0 for v in late.values()), late_requests=sum(v > 0 for v in late.values()),
                lateness_minutes=sum(late.values()), max_lateness_minutes=max(late.values(), default=0),
                mean_served_lateness_minutes=sum(late.values())/len(late) if late else None,
                charges=len(schedule['charges']), charging_wait_minutes=sum(waits),
                max_charging_wait_minutes=max(waits, default=0), charging_queue_peak=queue_peak,
                unrecharged_returns=sum(not c for _,_,c in dirty_events),
                censored_dirty_minutes=sum((b-a)*s['slot_minutes'] for a,b,c in dirty_events if not c),
                vehicle_utilization=ratio(vehicle_busy, available_vehicle_slots),
                charger_utilization=ratio(len(schedule['charges'])*s['charge_duration'], len(s['charger_ids'])*s['horizon']),
                technician_utilization=ratio(technician_busy,len(s['technician_ids'])*s['horizon']),
                maximum_regional_rejection_fraction=max_fraction,
                objective=sum(components.values()), objective_components=components,
                distributions=distributions)
