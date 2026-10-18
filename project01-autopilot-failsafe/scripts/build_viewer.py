#!/usr/bin/env python3
"""Build a portable, offline viewer from the retained experiment evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from string import Template
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    'evidence/full/comparison.json',
    'evidence/full/corpus-revision-review.json',
    'evidence/full/provenance-isolation-audit.json',
    'evidence/trace-inspection.json',
    'evidence/compound-ordering-inspection.json',
    'evidence/unit-tests.txt',
    'manifest.json',
    'src/failsafelab/evaluate.py',
]
SOURCES = ['scripts/build_viewer.py', 'viewer/template.html', 'viewer/viewer.css',
           'viewer/theme-init.js', 'viewer/viewer.js']


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def label(scenario: str) -> str:
    words = scenario.split('-', 1)[1].split('-')
    return ' '.join(word.upper() if word in {'gcs', 'rc', 'gps'} else (word.capitalize() if i == 0 else word)
                    for i, word in enumerate(words))


def build() -> str:
    summary = read_json(INPUTS[0])
    revision = read_json(INPUTS[1])
    audit = read_json(INPUTS[2])
    inspections = [read_json(path) for path in INPUTS[3:5]]
    manifest = read_json('manifest.json')
    rows = summary['runs']
    counts = Counter(row['outcome'] for row in rows)
    controls = [row for row in rows if row['negative_control']]
    failures = [row for row in rows if row['outcome'] != 'PASS' and not row['negative_control']]
    require(summary['complete'] and len(rows) == summary['completed_runs'] == summary['expected_runs'] == 58,
            'Viewer narrative requires the retained complete 58-run suite.')
    require(dict(counts) == summary['outcomes'] == {'PASS': 55, 'FAIL': 3}, 'Original outcomes changed.')
    require(len(controls) == 2 and all(row['outcome'] == 'FAIL' and row['control_accepted'] for row in controls),
            'Expected disabled-failsafe controls changed.')
    require(len(failures) == 1 and failures[0]['scenario_id'] == '11-gcs-battery-compound'
            and summary['gates_resolved'] is False, 'Preserved original text mismatch changed.')
    require(revision['original_summary_sha256'] == digest(ROOT / INPUTS[0]), 'Revision refers to a different original summary.')
    require(revision['original_results_preserved'] and revision['events_parameters_deadlines_and_state_assertions_unchanged']
            and revision['original_corpus_gates_resolved'] is False and revision['revised_corpus_gates_resolved']
            and revision['executed_corpus_version'] == '1.0.0' and revision['revised_corpus_version'] == '1.0.1',
            'Assertion-only revision scope changed.')
    require(len(revision['replays']) == 4 and all(row['revised_corpus_outcome'] == 'PASS' for row in revision['replays']),
            'Affected four-trace replay changed.')
    require(summary['evaluator_sha256'] == revision['evaluator_sha256'] == digest(ROOT / 'src/failsafelab/evaluate.py'),
            'Saved assessment does not match the retained evaluator.')
    require(audit['all_checks_passed'] and audit['runs_audited'] == 58 and audit['checks_evaluated'] == 522,
            'Saved provenance/isolation audit changed.')
    require(len(summary['replays']) == 2 and all(row['control_accepted'] for row in summary['replays']),
            'Saved wrong-mode replay acceptance changed.')
    inspection_rows = [row for data in inspections for row in data['runs']]
    require(len(inspection_rows) == 9 and len({row['run_dir'] for row in inspection_rows}) == 9,
            'Nine distinct retained onboard inspections expected.')
    tests = (ROOT / 'evidence/unit-tests.txt').read_text()
    require(re.search(r'Ran 41 tests in [^\n]+\n\nOK\s*$', tests) is not None, 'Recorded 41-test result changed.')
    parameters = summary['parameter_comparisons']
    require(len(parameters) == 12 and all(row['left_count'] == row['right_count'] == 1385
                                         and not row['differences'] for row in parameters),
            'Primary parameter comparison changed.')

    run_html = []
    for row in rows:
        run = row['run']
        require(not Path(run).is_absolute() and '..' not in Path(run).parts, 'Run path must remain local.')
        category = 'control' if row['negative_control'] else ('pass' if row['outcome'] == 'PASS' else 'mismatch')
        interpretation = {'control': 'Expected disabled-failsafe failure', 'pass': 'Original assertions passed',
                          'mismatch': 'Preserved text-assertion mismatch'}[category]
        responses = '<br>'.join(f"{escape(value['after'])}: {value['latency_s']:.3f} / {value['deadline_s']:g} s"
                                for value in row['mode_responses']) or 'No matched transition'
        details = '; '.join(f"{item['outcome']}: {item['detail']}" for item in row['nonpassing'])
        result_link = f'evidence/full/{run}/result.json'
        seal_link = f'evidence/full/{run}/SHA256SUMS'
        run_html.append(f'''<tr data-release="{escape(row['version'])}" data-outcome="{category}">
<th scope="row">{escape(label(row['scenario_id']))}<small>{escape(row['scenario_id'])}</small></th>
<td>{escape(row['version'])}</td><td>{row['schedule_offset_s']:g} s</td>
<td><span class="status {category}">{escape(row['outcome'])}</span><small>{interpretation}</small></td>
<td class="numeric">{responses}</td><td><a href="{escape(result_link)}">Result JSON</a><br><a href="{escape(seal_link)}">SHA-256 seal</a>
{('<details><summary>Assertion details</summary><p>' + escape(details) + '</p></details>') if details else ''}</td></tr>''')

    chart_rows = []
    primary = {(row['scenario_id'], row['version']): row for row in rows if row['schedule_offset_s'] == 0}
    for pair in parameters:
        scenario = pair['scenario_id']
        cells = []
        for version in ('4.5.6', '4.5.7'):
            responses = primary[scenario, version]['mode_responses']
            if responses:
                latency = max(value['latency_s'] for value in responses)
                require(0 <= latency <= 8, 'Primary chart scale needs review.')
                cells.append(f'<td class="latency"><span class="bar release-{version[-1]}" style="width:{latency / 8 * 100:.3f}%" aria-hidden="true"></span><span class="bar-label">{latency:.3f} s</span></td>')
            else:
                cells.append('<td class="latency"><span class="bar-label">No LAND assertion</span></td>')
        chart_rows.append(f'<tr><th scope="row">{escape(label(scenario))}</th>{"".join(cells)}</tr>')

    replays = ''.join(f'''<tr><th scope="row">{escape(row['run'].split('/')[0])}</th><td>{escape(row['run'].split('/')[-1].replace('schedule-', ''))} s</td><td><span class="status {'mismatch' if row['executed_corpus_outcome'] == 'FAIL' else 'pass'}">{escape(row['executed_corpus_outcome'])}</span></td><td><span class="status pass">{escape(row['revised_corpus_outcome'])}</span></td><td><a href="evidence/full/{escape(row['result'])}">Replay JSON</a></td></tr>'''
                      for row in revision['replays'])
    pins = ''.join(f'<li><strong>ArduCopter {escape(pin["version"])}</strong><code>{escape(pin["commit"])}</code></li>'
                   for pin in manifest['releases'])
    replacements = {
        'theme_init': (ROOT / 'viewer/theme-init.js').read_text(),
        'style': (ROOT / 'viewer/viewer.css').read_text(),
        'behavior': (ROOT / 'viewer/viewer.js').read_text(),
        'run_rows': '\n'.join(run_html), 'chart_rows': '\n'.join(chart_rows),
        'replay_rows': replays, 'release_pins': pins,
        'summary_hash': digest(ROOT / INPUTS[0]),
    }
    html = Template((ROOT / 'viewer/template.html').read_text()).substitute(replacements)
    check_links(html)
    return html


def check_links(html: str) -> None:
    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key != 'href' or not value:
                    continue
                url = urlsplit(value)
                if url.scheme or url.netloc or not url.path:
                    continue
                path = (ROOT / unquote(url.path)).resolve()
                generated = {'index.html', 'viewer-manifest.json'}
                require(path.is_relative_to(ROOT) and (path.is_file() or url.path in generated),
                        f'Missing or out-of-project link: {value}')
    Links().feed(html)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify exact generated HTML and provenance without writing.')
    args = parser.parse_args()
    html = build().encode()
    provenance = {
        'schema_version': 1,
        'purpose': 'Saved-results presentation only; no new SITL execution or operational validation.',
        'generator': 'python3 scripts/build_viewer.py',
        'inputs': {path: digest(ROOT / path) for path in INPUTS},
        'sources': {path: digest(ROOT / path) for path in SOURCES},
        'outputs': {'index.html': hashlib.sha256(html).hexdigest()},
    }
    artifacts = {'index.html': html, 'viewer-manifest.json': (json.dumps(provenance, indent=2) + '\n').encode()}
    if args.check:
        stale = [path for path, content in artifacts.items() if not (ROOT / path).exists() or (ROOT / path).read_bytes() != content]
        if stale:
            print('Stale viewer artifact(s): ' + ', '.join(stale))
            return 1
        print('Viewer exact: 58 original runs, 4 retrospective replays, 522 audit checks, 9 inspections; all local links exist.')
    else:
        for path, content in artifacts.items():
            (ROOT / path).write_bytes(content)
        print('Wrote index.html and viewer-manifest.json from retained evidence.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
