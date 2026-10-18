import copy
import json
from pathlib import Path
import pytest
from dispatch.checker import validate_schedule
from dispatch.metrics import summarize
from dispatch.optimize import optimize, online_optimize


def hand():
    return json.loads((Path(__file__).parents[1]/'fixtures/hand_four.json').read_text())


def test_hand_optimum():
    s = hand()
    a = optimize(s, time_limit=5)
    assert validate_schedule(s, a) == []
    assert summarize(s, a)['objective'] == pytest.approx(2)
    assert a['solver']['status'] == 0
    assert a['solver']['lower_bound'] == pytest.approx(2)
    assert a['solver']['relative_gap'] == pytest.approx(0)


@pytest.mark.parametrize('change', ['empty', 'no_vehicle', 'no_charger', 'no_staff', 'cancelled', 'beyond_horizon'])
def test_boundaries(change):
    s = hand()
    if change == 'empty': s['requests'] = []
    if change == 'no_vehicle': s['vehicles'] = []
    if change == 'no_charger': s['charger_ids'] = []
    if change == 'no_staff': s['technician_ids'] = []
    if change == 'cancelled':
        for r in s['requests']: r['cancelled'] = True
    if change == 'beyond_horizon':
        for r in s['requests']: r['release'] = s['horizon']
    a = optimize(s, time_limit=3)
    assert validate_schedule(s, a) == []
    expected = 2 if change == 'no_charger' else 0
    assert len(a['services']) == expected


def test_limit_fallback_is_feasible_and_honest():
    s = hand()
    a = optimize(s, time_limit=0)
    assert validate_schedule(s,a) == []
    assert a['solver']['status'] == 1
    assert a['solver']['used_fallback']
    assert not a['solver']['optimal']


def test_online_does_not_see_future():
    s = hand()
    s['requests'][-1]['release'] = 6
    other = copy.deepcopy(s)
    other['requests'][-1]['deadline'] = 100
    other['requests'][-1]['priority'] = 99
    a = online_optimize(s, time_limit=2)
    b = online_optimize(other, time_limit=2)
    assert validate_schedule(s,a) == []
    assert [x for x in a['decisions'] if x['time'] < 6] == [x for x in b['decisions'] if x['time'] < 6]
    assert a['solver']['lower_bound'] is None


def test_preserves_external_prefix_resource_identities():
    s = hand()
    fixed = dict(request_id='R1',vehicle_id='V1',battery_id='B2',technician_id='T2',start=0,delivery=2,end=2)
    prefix = dict(services=[fixed],charges=[])
    a = optimize(s,time_limit=3,now=1,prefix=prefix)
    assert next(x for x in a['services'] if x['request_id']=='R1') == fixed
    assert validate_schedule(s,a) == []
