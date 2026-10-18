"""Qualify a negative control by its intended mismatch, not its headline verdict."""
def control_accepted(result, kind):
    if result.get('outcome') != 'FAIL' or not result.get('checks') or any(c['outcome']!='PASS' for c in result['checks']):
        return False
    assertions=result.get('assertions',[])
    modes=[a for a in assertions if a['type']=='mode']
    gaps=[a for a in assertions if a['type']=='heartbeat_gap']
    if not modes or not gaps or any(a['outcome']!='FAIL' for a in modes) or any(a['outcome']!='PASS' for a in gaps):
        return False
    if kind=='wrong-mode':
        return all(a['outcome']=='PASS' for a in assertions if a['type']!='mode')
    if kind=='disabled':
        disarmed=[a for a in assertions if a['type']=='disarmed']
        if not disarmed or any(a['outcome']!='FAIL' for a in disarmed):return False
        observed=[r for a in modes+disarmed for r in a.get('observations',[])]
        return bool(observed) and all(r['mode']==4 and r['armed'] for r in observed) and all(a['outcome']!='PASS' for a in assertions if a['type']=='text')
    return False
