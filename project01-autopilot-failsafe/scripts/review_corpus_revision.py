#!/usr/bin/env python3
"""Explicit retrospective check of corpus 1.0.1; preserve executed 1.0.0 results."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from failsafelab.evaluate import evaluate_run


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('suite', type=Path)
    args = parser.parse_args()
    suite = args.suite.resolve()
    summary_path = suite / 'comparison.json'
    summary = json.loads(summary_path.read_text())
    evaluator_hash = digest(ROOT / 'src/failsafelab/evaluate.py')
    if summary['evaluator_sha256'] != evaluator_hash:
        raise SystemExit('First re-evaluate the original suite with the current evaluator.')
    spec_path = ROOT / 'scenarios/11-gcs-battery-compound.json'
    old_path = ROOT / 'scenarios/history/1.0.0/11-gcs-battery-compound.json'
    old = json.loads(old_path.read_text())
    revised = json.loads(spec_path.read_text())
    expected = copy.deepcopy(old)
    assert expected['assertions'][1].pop('contains') == 'GCS Failsafe'
    expected['assertions'][1]['contains_any'] = [
        'GCS Failsafe', 'GCS + Battery Failsafe - Continuing Landing']
    if revised != expected:
        raise SystemExit('Revision differs beyond the reviewed text-alternative correction.')
    rows = []
    accepted = []
    for row in summary['runs']:
        if row['scenario_id'] == revised['id']:
            case = suite / row['run']
            if json.loads((case / 'scenario.json').read_text()) != old:
                raise SystemExit('Sealed executed scenario is not the recorded 1.0.0 scenario.')
            result = evaluate_run(case, scenario_override=revised)
            target = suite / 'corpus-1.0.1-replay' / (row['run'].replace('/', '__') + '.json')
            target.parent.mkdir(exist_ok=True)
            target.write_text(json.dumps(result, indent=2) + '\n')
            rows.append({'run': row['run'], 'executed_corpus_outcome': row['outcome'],
                         'revised_corpus_outcome': result['outcome'],
                         'original_scenario_sha256': digest(case / 'scenario.json'),
                         'raw_seal_sha256': digest(case / 'SHA256SUMS'),
                         'result': str(target.relative_to(suite))})
            accepted.append(result['outcome'] == 'PASS')
        else:
            accepted.append(row['control_accepted'] is True if row['negative_control']
                            else row['outcome'] == 'PASS')
    resolved = (summary['completed_runs'] == summary['expected_runs'] == 58
                and len(rows) == 4 and all(accepted) and not summary['cleanup_violations']
                and len(summary['replays']) == 2
                and all(row['control_accepted'] for row in summary['replays']))
    result = {'schema_version': 1, 'method': 'Retrospective assertion-only replay; no new SITL execution',
              'executed_corpus_version': '1.0.0', 'revised_corpus_version': '1.0.1',
              'original_summary_sha256': digest(summary_path),
              'evaluator_sha256': evaluator_hash, 'revised_scenario_sha256': digest(spec_path),
              'review_basis': 'docs/compound-ordering-review.md and pinned events.cpp lines 208-211',
              'only_change': 'Permit the explicit GCS plus Battery status branch as an alternative to GCS Failsafe',
              'events_parameters_deadlines_and_state_assertions_unchanged': True,
              'original_results_preserved': True,
              'original_corpus_gates_resolved': summary['gates_resolved'],
              'revised_corpus_gates_resolved': resolved, 'replays': rows}
    (suite / 'corpus-revision-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if resolved else 1


if __name__ == '__main__':
    raise SystemExit(main())
