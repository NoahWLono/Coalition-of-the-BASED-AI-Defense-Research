"""Inventory current publishable files without building a duplicate source ZIP."""
import hashlib
import json
from pathlib import Path

from clean_reproduce import fingerprint
from release import source_files

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'artifacts/DELIVERY_MANIFEST.json'


def run():
    files = {}
    for _, path in source_files(ROOT):
        if path == DESTINATION:
            continue
        payload = path.read_bytes()
        files[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
    record = {
        'scope': 'Current publishable file inventory after the appearance update. Excludes this manifest, dist archives, runtime state, virtual environments, caches and Git metadata. Hashes establish file consistency only.',
        'functional_tree_sha256': fingerprint(ROOT),
        'historical_validation': 'Original clean-reproduction and browser records describe the prior light-appearance version. See docs/THEME_REFRESH.md and artifacts/history/light-appearance/DELIVERY_MANIFEST.json.',
        'files': files,
    }
    DESTINATION.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'manifest': str(DESTINATION.relative_to(ROOT)), 'files': len(files), 'functional_tree_sha256': record['functional_tree_sha256']}))


if __name__ == '__main__':
    run()
