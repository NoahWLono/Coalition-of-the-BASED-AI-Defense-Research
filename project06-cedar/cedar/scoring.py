"""Transparent criterion intervals and deterministic sensitivity, never win probabilities."""
PROFILES = {
    'balanced': {'label':'Balanced review','operations':1,'support':1},
    'operations': {'label':'Capability priority','operations':3,'support':1},
    'support': {'label':'Service continuity','operations':1,'support':3}}


def normalize_score(value, requirement):
    s = requirement['scoring']
    fraction=(float(value)-s['low'])/(s['high']-s['low'])
    if s['direction']=='lower':
        fraction=1-fraction
    return round(100*max(0,min(1,fraction)),6)


def weight(req, profile):
    # Preference groups use the requirement's declared commercial category.
    return PROFILES[profile]['operations' if req.get('category')=='operations' else 'support']


def score_package(requirements, assessments, profile, weights=None):
    criteria=[r for r in requirements if r['mode']=='scored']
    amap={a['requirement_id']:a for a in assessments}
    criteria=[r for r in criteria if amap[r['id']]['state']!='not_applicable']
    raw={r['id']:(weights or {}).get(r['id'],weight(r,profile)) for r in criteria}
    total=sum(raw.values())
    rows=[]
    for r in criteria:
        a=amap[r['id']]; w=raw[r['id']]/total if total else 0
        rows.append(dict(requirement_id=r['id'],weight=raw[r['id']],normalized_weight=w,
            low=a.get('score_low',0),high=a.get('score_high',100),
            contribution_low=w*a.get('score_low',0),contribution_high=w*a.get('score_high',100),state=a['state']))
    return {'low':round(sum(r['contribution_low'] for r in rows),4),
        'high':round(sum(r['contribution_high'] for r in rows),4),'contributions':rows,
        'method':'Clamp each declared min-max criterion to [0,100]. Unknown evidence spans [0,100]. Applicable weights sum to one; informational and mandatory gates do not add score.'}


def sensitivity(packages,requirements):
    eligible=[p for p in packages if p['eligible']]
    cases=[]
    # A deterministic family of group weights; not sampled from a statistical population.
    for factor in [0.25,0.5,1,2,4]:
        weights={r['id']:factor if r.get('category')=='operations' else 1 for r in requirements if r['mode']=='scored'}
        scored=[(p,score_package(requirements,p['assessments'],'balanced',weights)) for p in eligible]
        best_lower=max([s['low'] for p,s in scored],default=0)
        possible=[p['id'] for p,s in scored if s['high']>=best_lower-1e-7]
        guaranteed=[p['id'] for p,s in scored if all(s['low']>t['high']+1e-7 for q,t in scored if p['id']!=q['id'])]
        cases.append({'operations_to_support':factor,'possible_leaders':possible,'guaranteed_leaders':guaranteed})
    return {'cases':cases,'interpretation':'Five explicit group-weight ratios (0.25, 0.5, 1, 2, 4), restricted to documentary-eligible bids. These are scenario comparisons, not probabilities of purchase success.'}


def dominance(packages):
    results=[]
    valid=[p for p in packages if p['eligible'] and p['cost']['upper_total'] is not None]
    for a in valid:
        for b in valid:
            if a['id']==b['id']:continue
            ac={x['requirement_id']:x for x in a['score']['contributions']}
            bc={x['requirement_id']:x for x in b['score']['contributions']}
            if ac.keys()!=bc.keys():continue
            weak=a['cost']['upper_total']<=b['cost']['known_total'] and all(ac[k]['low']>=bc[k]['high'] for k in ac)
            strict=a['cost']['upper_total']<b['cost']['known_total'] or any(ac[k]['low']>bc[k]['high'] for k in ac)
            if weak and strict:results.append({'dominant':a['id'],'dominated':b['id']})
    return results
