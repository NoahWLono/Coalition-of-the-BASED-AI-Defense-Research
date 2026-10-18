"""Refresh report appearance while preserving each exported decision envelope.

The original four API-replay ZIPs are retained once for the historical logs.
The browser's downloaded ZIP is historical capture evidence and is not changed.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cedar.export import build_package, verify_package


def members(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def run():
    history = ROOT / 'artifacts/history/light-appearance'
    history.mkdir(parents=True, exist_ok=True)
    old_manifest = ROOT / 'artifacts/DELIVERY_MANIFEST.json'
    if not (history / old_manifest.name).exists():
        (history / old_manifest.name).write_bytes(old_manifest.read_bytes())
    results = []
    for name in ['full-decision.zip', 'full-stale-decision.zip', 'slice-decision.zip', 'slice-stale-decision.zip']:
        path = ROOT / 'artifacts' / name
        original = history / name
        if not original.exists():
            original.write_bytes(path.read_bytes())
        old_bytes = original.read_bytes()
        old_check = verify_package(old_bytes)
        if not old_check['valid']:
            raise ValueError(old_check)
        old = members(old_bytes)
        envelope = json.loads(old['decision.json'])
        new_bytes = build_package(envelope)
        new = members(new_bytes)
        checked = verify_package(new_bytes)
        if not checked['valid']:
            raise ValueError(checked)
        # Only rendering, bundled verifier source, and the corresponding manifest change.
        changed = sorted(k for k in old if old[k] != new[k])
        if set(old) != set(new) or set(changed) - {'report.html', 'verify.py', 'manifest.json'}:
            raise ValueError('Theme update changed decision evidence: ' + name)
        path.write_bytes(new_bytes)
        results.append({'package': str(path.relative_to(ROOT)), 'historical_package': str(original.relative_to(ROOT)),
            'original_sha256': hashlib.sha256(old_bytes).hexdigest(), 'sha256': hashlib.sha256(new_bytes).hexdigest(),
            'changed_members': changed, 'decision_json_byte_identical': True,
            'evidence_csv_and_sources_byte_identical': True, 'verification': checked})
    report = {'scope': 'Report appearance refresh only. Original decision bytes, digests, review events, current/stale states, citations and sources are preserved. Historical browser/PDF/video evidence was not regenerated.', 'packages': results}
    (ROOT / 'artifacts/theme-package-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
