"""Fixed seeded synthetic scenarios. No external dataset or geography."""
import copy
import json
import random
from pathlib import Path
from .schema import validate_scenario

REGIONS = ['Alder', 'Birch', 'Cedar', 'Dune']


def benchmark(seed=1801, count=20):
    rng = random.Random(seed)
    nodes = ['Depot'] + REGIONS
    travel = {a: {b: 0 if a == b else rng.randint(1, 4) for b in nodes} for a in nodes}
    # Dune represents a longer abstract service, without geographical claims.
    travel['Depot']['Dune'] = 5
    travel['Dune']['Depot'] = 4
    requests = []
    for i in range(count):
        release = rng.randrange(0, 25)
        region = REGIONS[i % 4]
        requests.append(dict(id=f'R{i+1:02}', release=release,
                             deadline=release + rng.randint(6, 15), region=region,
                             category=['standard', 'protected'][i % 2],
                             priority=2 if i % 5 == 0 else 1, cancelled=(i == 18)))
    s = dict(id=f'benchmark_s{seed}_n{count}', seed=seed, horizon=48, slot_minutes=5,
             load_time=1, handoff_time=1, turnaround_time=1, charge_duration=4,
             vehicles=[dict(id='V1', unavailable=[[18, 23]]),
                       dict(id='V2', unavailable=[[30, 35]]),
                       dict(id='V3', unavailable=[])],
             battery_ids=['B1', 'B2', 'B3', 'B4'], charger_ids=['C1'],
             technician_ids=['T1', 'T2'], travel=travel, requests=requests,
             weights=dict(rejection=200, lateness=1, charge=1, fairness=100))
    return validate_scenario(s)


def sensitivity_cases(base):
    """One factor at a time, with exact paired demand and disruption inputs."""
    yield 'baseline', copy.deepcopy(base)
    for count in (12, 28):
        yield f'demand_{count}', benchmark(base['seed'], count)
    for count in (0, 2):
        s = copy.deepcopy(base)
        s['charger_ids'] = [f'C{i+1}' for i in range(count)]
        s['id'] += f'_chargers{count}'
        yield f'chargers_{count}', s
    s = copy.deepcopy(base)
    for v in s['vehicles']:
        v['unavailable'] = []
    s['id'] += '_clear'
    yield 'weather_clear', s
    s = copy.deepcopy(base)
    for v in s['vehicles']:
        v['unavailable'] = [[12, 30]]
    s['id'] += '_severe'
    yield 'weather_severe', s
    for key, value in [('rejection', 20), ('rejection', 1000), ('lateness', 10),
                       ('fairness', 0), ('fairness', 2000)]:
        s = copy.deepcopy(base)
        s['weights'][key] = value
        s['id'] += f'_{key}{value}'
        yield f'{key}_{value}', s


def main():
    out = Path(__file__).resolve().parents[1] / 'fixtures'
    out.mkdir(exist_ok=True)
    for name, s in sensitivity_cases(benchmark()):
        (out / f'{name}.json').write_text(json.dumps(s, indent=2) + '\n')


if __name__ == '__main__':
    main()
