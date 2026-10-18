from copy import deepcopy
import pytest
from dispatch.generate import benchmark, sensitivity_cases
from dispatch.schema import validate_scenario, durations


def test_reproducible_paired_demand():
    s = benchmark()
    assert s == benchmark()
    assert len(s['requests']) == 20
    assert benchmark(count=28)['requests'][:20] == s['requests']
    assert len(list(sensitivity_cases(s))) == 12
    assert all(durations(s, r)[0] <= durations(s, r)[1] for r in s['requests'])


@pytest.mark.parametrize('field,value', [('horizon', 0), ('load_time', -1), ('slot_minutes', 0)])
def test_invalid_input(field, value):
    s = deepcopy(benchmark())
    s[field] = value
    with pytest.raises(ValueError):
        validate_scenario(s)


@pytest.mark.parametrize('change', ['numeric_request','numeric_vehicle','missing_category','incomplete_matrix'])
def test_schema_rejects_invalid_contract(change):
    s = benchmark()
    if change=='numeric_request': s['requests'][0]['id']=7
    if change=='numeric_vehicle': s['vehicles'][0]['id']=7
    if change=='missing_category': del s['requests'][0]['category']
    if change=='incomplete_matrix': del s['travel']['Alder']['Birch']
    with pytest.raises(ValueError): validate_scenario(s)
