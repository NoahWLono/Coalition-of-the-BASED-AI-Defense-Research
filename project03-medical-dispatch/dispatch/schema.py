"""Input validation and administrative timing definitions."""
import math


def durations(s, r):
    delivery = s['load_time'] + s['travel']['Depot'][r['region']] + s['handoff_time']
    return delivery, delivery + s['travel'][r['region']]['Depot'] + s['turnaround_time']


def validate_scenario(s):
    def integer(x, low=0):
        return type(x) is int and x >= low
    def named(x):
        return isinstance(x,str) and bool(x)
    if not isinstance(s,dict) or not named(s.get('id')):
        raise ValueError('scenario must have a nonempty string id')
    required = ('horizon','slot_minutes','load_time','handoff_time','turnaround_time',
                'charge_duration','vehicles','battery_ids','charger_ids','technician_ids',
                'requests','travel','weights')
    if any(k not in s for k in required):
        raise ValueError('missing scenario field')
    for key in ('horizon', 'slot_minutes', 'load_time', 'charge_duration'):
        if not integer(s[key], 1):
            raise ValueError(f'{key} must be a positive integer')
    for key in ('handoff_time', 'turnaround_time'):
        if not integer(s[key]):
            raise ValueError(f'{key} must be a nonnegative integer')
    for key in ('battery_ids', 'charger_ids', 'technician_ids'):
        ids = s[key]
        if len(set(ids)) != len(ids) or any(not isinstance(x, str) or not x for x in ids):
            raise ValueError(f'{key} must contain unique nonempty strings')
    vehicles = s['vehicles']
    if any(not named(v.get('id')) for v in vehicles):
        raise ValueError('vehicle IDs must be nonempty strings')
    if len({v['id'] for v in vehicles}) != len(vehicles):
        raise ValueError('duplicate vehicle')
    for v in vehicles:
        for a, b in v['unavailable']:
            if not (integer(a) and integer(b) and a < b <= s['horizon']):
                raise ValueError('invalid unavailability interval')
    ids = set()
    for r in s['requests']:
        if any(k not in r for k in ('id','release','deadline','priority','cancelled','region','category')):
            raise ValueError('missing request field')
        if any(not named(r[k]) for k in ('id','region','category')):
            raise ValueError('request ID, region and category must be nonempty strings')
        if r['id'] in ids:
            raise ValueError('duplicate request')
        ids.add(r['id'])
        if not integer(r['release']) or not integer(r['deadline']) or not integer(r['priority'], 1):
            raise ValueError('invalid request time or priority')
        if type(r['cancelled']) is not bool:
            raise ValueError('cancelled must be boolean')
        if r['region'] not in s['travel']:
            raise ValueError('request region missing from travel matrix')
    nodes = set(s['travel'])
    if 'Depot' not in nodes or any(not named(x) for x in nodes):
        raise ValueError('travel matrix must include Depot and named nodes')
    if any(not isinstance(row,dict) or set(row) != nodes for row in s['travel'].values()):
        raise ValueError('travel matrix must be complete and square')
    for row in s['travel'].values():
        if any(not integer(t) for t in row.values()):
            raise ValueError('travel must be nonnegative integer slots')
    for k in ('rejection', 'lateness', 'charge', 'fairness'):
        w = s['weights'][k]
        if isinstance(w, bool) or not isinstance(w, (float, int)) or not math.isfinite(w) or w < 0:
            raise ValueError('weights must be finite and nonnegative')
    return s
