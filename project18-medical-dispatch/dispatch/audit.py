"""Reopen every exported schedule and independently recheck its feasibility."""
import argparse
import json
from pathlib import Path
from .checker import validate_schedule
from .metrics import summarize


def audit(out):
    checked=0
    for path in sorted((out/'schedules').glob('*.json')):
        name=path.stem.split('__')[0]
        scenario=json.loads((out/'scenarios'/f'{name}.json').read_text())
        schedule=json.loads(path.read_text())
        errors=validate_schedule(scenario,schedule)
        if errors: raise AssertionError(f'{path}: {errors}')
        actual=summarize(scenario,schedule)
        saved=json.loads((out/'metrics'/path.name).read_text())
        if actual != saved: raise AssertionError(f'{path}: saved metrics mismatch')
        solver=schedule['solver']
        lower=solver.get('lower_bound')
        if lower is not None and lower > actual['objective']+1e-5:
            raise AssertionError(f'{path}: lower bound exceeds feasible objective')
        requests={r['id']:r for r in scenario['requests']}
        for decision in schedule.get('decisions',[]):
            t=decision['time']
            visible={rid for rid,r in requests.items() if r['release'] <= t}
            if set(decision['visible_request_ids']) != visible:
                raise AssertionError(f'{path}: visibility log mismatch at {t}')
            for action in decision['service_starts']:
                if action not in schedule['services'] or action['request_id'] not in visible or action['start'] != t:
                    raise AssertionError(f'{path}: execution log mismatch')
            for action in decision['charge_starts']:
                if action not in schedule['charges'] or action['start'] != t:
                    raise AssertionError(f'{path}: charge log mismatch')
        checked+=1
    if checked==0: raise AssertionError('no exported schedules found')
    tiny=json.loads((out/'tiny_agreement.json').read_text())
    if any(abs(t['objective']-t['reference_objective'])>1e-6 or t['status']!=0 for t in tiny):
        raise AssertionError('tiny agreement record failed')
    return dict(valid=True,schedules=checked,tiny_agreements=len(tiny))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('results',type=Path)
    args=p.parse_args()
    print(json.dumps(audit(args.results),indent=2))


if __name__=='__main__': main()
