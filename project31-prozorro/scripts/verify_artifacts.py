"""Verify saved extract/output digests, sample boundaries and real/synthetic separation."""
from pathlib import Path
import hashlib
import json
import re

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'output/real/SHA256SUMS.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256((root/'output/real'/name).read_bytes()).hexdigest()==digest, name
provenance=json.loads((root/'output/real/provenance.json').read_text())
records=json.loads((root/'output/real/normalized.json').read_text())
assert len(records)==50
assert len({r['key'] for r in records})==50
for row in provenance:
    p=root/'data/extracts'/row['extract_file']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['extract_sha256'],p
for r in records:
    assert r['source_kind']=='real'
    assert '2025-01-01'<=r['publication_date'][:10]<='2025-03-31'
    assert r['tenderID'][3:13]==r['publication_date'][:10]
    assert r['review']['annotator_type']=='assistant'
    assert r['comparison_eligible'] is False
for p in (root/'data/extracts').glob('*.json'):
    text=p.read_text()
    for forbidden in ['"contactPoint"','"deliveryAddress"','"deliveryLocation"','"suppliers"','"bankAccount"']:
        assert forbidden not in text,(p,forbidden)
    assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\+380[\s()\d-]{9,}',text),p
evaluation=json.loads((root/'output/real/evaluation.json').read_text())
assert evaluation['accepted_label_count']==0
assert all(x['estimate'] is None and x['denominator']==0 for x in evaluation['metrics'].values())
demo=json.loads((root/'output/synthetic/checks.json').read_text())
assert demo['actual_lead_keys']==demo['expected_lead_keys']
assert demo['common_currency_scaling_preserves_leads']
print('Artifact verification passed: 50 unique real lots; source and output hashes; period; privacy field scan; null unlabeled metrics; separate synthetic expectations.')
