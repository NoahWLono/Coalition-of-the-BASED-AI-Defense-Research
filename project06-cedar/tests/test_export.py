"""Package boundaries: portable evidence, inert output and consistency failures."""
import csv
import base64
import hashlib
import importlib.util
import io
import json
import html as html_module
import re
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


def exporter():
    # Explicit failure until the implementation exists, rather than collection error.
    assert importlib.util.find_spec('cedar.export'), 'Portable export module must exist'
    from cedar import export
    return export


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def snapshot():
    from cedar.engine import evaluate
    from test_engine import doc, req, row
    old = doc(row(), '=old/../../danger')
    old.update(title='=FORMULA() <script>alert(1)</script>', path='../../old.md', hash=hashlib.sha256(old['content'].encode()).hexdigest())
    new = doc(row(), 'new')
    new.update(title='Amended evidence', path='new.md', supersedes=[old['id']], hash=hashlib.sha256(new['content'].encode()).hexdigest())
    requirement=req();requirement.update(wording='Six synthetic aircraft',category='operations',version='v1',source='Synthetic policy')
    inputs=dict(schema_version='1.0',suppliers=[{'id':'s1','name':'Supplier'}], packages=[{'id':'p1','supplier_id':'s1','name':'Package'}], requirements=[requirement], requirements_versions={'v1':[requirement]},requirements_version='v1',documents=[old,new],structured={'inventory/a.json':{'content':'{"example":true}', 'hash':hashlib.sha256(b'{"example":true}').hexdigest()}},available_amendments=[],applied_amendments=['amendment'])
    ev=evaluate(inputs)
    ev['assertions'][0]['note']='\t=HYPERLINK("https://example.invalid")'
    record=dict(schema_version='1.0', application_version='0.1.0', created_at='2026-10-17T12:00:00Z',revision=2,inputs=inputs,assumptions=ev['assumptions'],profile='balanced',as_of='2026-10-17',reviews={},evaluation=ev,package_id='p1',decision='conditional',rationale='<img src=x onerror=alert(1)>',limitations=ev['limitations'])
    return dict(id='snapshot-1',digest=hashlib.sha256(canonical(record)).hexdigest(),revision=2,record=record,review=None,approval=None,current=False,status='stale')


def unpack(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        return {name:z.read(name) for name in z.namelist()}


def repack(files, refresh_manifest=False):
    if refresh_manifest:
        manifest=json.loads(files['manifest.json'])
        manifest['files']={name:{'sha256':hashlib.sha256(body).hexdigest(),'size':len(body)} for name,body in files.items() if name!='manifest.json'}
        files['manifest.json']=canonical(manifest)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,body in files.items():z.writestr(name,body)
    return buf.getvalue()


def replace_decision(files, change, refresh_digest=True):
    data=json.loads(files['decision.json']);change(data)
    if refresh_digest:
        data['digest']=hashlib.sha256(canonical(data['record'])).hexdigest()
        manifest=json.loads(files['manifest.json']);manifest['digest']=data['digest']
        files['manifest.json']=canonical(manifest)
    files['decision.json']=canonical(data)
    return repack(files,True)


def test_package_preserves_snapshot_and_inert_sources():
    module=exporter(); snap=snapshot();payload=module.build_package(snap)
    result=module.verify_package(payload)
    assert result['valid'],result['errors']
    files=unpack(payload)
    assert json.loads(files['decision.json'])==snap
    assert len([n for n in files if n.startswith('sources/')])==3
    assert all(n.endswith('.txt') and '..' not in n for n in files if n.startswith('sources/'))
    assert any(body==snap['record']['inputs']['documents'][0]['content'].encode() for n,body in files.items() if n.startswith('sources/'))
    html=files['report.html'].decode()
    assert '<script>alert(1)</script>' not in html
    assert '<img src=x onerror=alert(1)>' not in html
    assert '&lt;img' in html and 'stale' in html.lower()
    assert 'No finite upper bound' in html
    assert 'Superseded' in html


def test_csv_neutralizes_formula_and_control_prefixes():
    module=exporter();files=unpack(module.build_package(snapshot()))
    rows=list(csv.DictReader(io.StringIO(files['evidence.csv'].decode())))
    assert rows
    for row in rows:
        for value in row.values():
            assert not value.lstrip(' \t\r\n').startswith(('=','+','-','@'))
    assert any("'=old" in str(row) for row in rows)
    assert any(row["note"].startswith("'\t=HYPERLINK") for row in rows)


def test_report_csp_allows_only_exact_appearance_controller():
    module = exporter()
    report = unpack(module.build_package(snapshot()))['report.html'].decode()
    scripts = re.findall(r'<script>(.*?)</script>', report, re.S)
    assert scripts == [module.theme_script()]
    policy = html_module.unescape(re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', report).group(1))
    expected = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    assert "script-src 'sha256-" + expected + "';" in policy
    assert "default-src 'none'" in policy and "form-action 'none'" in policy
    assert "script-src 'unsafe-inline'" not in policy
    assert '<script>alert(1)</script>' not in report
    assert report.index('<script>') < report.index('<style>')


@pytest.mark.parametrize('filename',['report.html','decision.json','evidence.csv','verify.py'])
def test_manifest_catches_byte_tampering(filename):
    module=exporter();files=unpack(module.build_package(snapshot()));files[filename]+=b'tampered'
    assert not module.verify_package(repack(files))['valid']


def test_citations_checked_even_if_manifest_and_record_digest_recomputed():
    module=exporter();files=unpack(module.build_package(snapshot()))
    payload=replace_decision(files,lambda data:data['record']['evaluation']['assertions'][0].update(original='Invented replacement claim'))
    result=module.verify_package(payload)
    assert not result['valid'] and any('citation' in e.lower() for e in result['errors'])


def test_source_hash_checked_even_if_manifest_and_record_digest_recomputed():
    module=exporter();files=unpack(module.build_package(snapshot()))
    payload=replace_decision(files,lambda data:data['record']['inputs']['documents'][0].update(hash='0'*64))
    result=module.verify_package(payload)
    assert not result['valid'] and any('source' in e.lower() for e in result['errors'])


def test_selected_requirement_consistency():
    module=exporter();files=unpack(module.build_package(snapshot()))
    payload=replace_decision(files,lambda data:data['record']['evaluation']['requirements'][0].update(target=999))
    result=module.verify_package(payload)
    assert not result['valid'] and any('requirement' in e.lower() for e in result['errors'])


@pytest.mark.parametrize('name',['../escape.txt','/absolute.txt','sources/../escape.txt','sources\\escape.txt','extra.py'])
def test_rejects_unsafe_or_unexpected_names(name):
    module=exporter();files=unpack(module.build_package(snapshot()));files[name]=b'irrelevant'
    result=module.verify_package(repack(files,True))
    assert not result['valid']


def test_duplicate_zip_members_rejected():
    module=exporter();payload=module.build_package(snapshot());buf=io.BytesIO(payload)
    with pytest.warns(UserWarning):
        with zipfile.ZipFile(buf,'a') as z:z.writestr('report.html',b'duplicate')
    assert not module.verify_package(buf.getvalue())['valid']


def test_large_expansion_rejected_before_reading():
    module=exporter();buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('decision.json',b'0'*(17*1024*1024))
    result=module.verify_package(buf.getvalue())
    assert not result['valid'] and any('limit' in e.lower() for e in result['errors'])


def test_embedded_verifier_runs_without_project(tmp_path):
    module=exporter();payload=module.build_package(snapshot());files=unpack(payload)
    (tmp_path/'verify.py').write_bytes(files['verify.py']);(tmp_path/'decision.zip').write_bytes(payload)
    run=subprocess.run([sys.executable,'-I',str(tmp_path/'verify.py'),str(tmp_path/'decision.zip')],capture_output=True,text=True,cwd=tmp_path)
    assert run.returncode==0,run.stderr+run.stdout
    assert json.loads(run.stdout)['valid']
    files['report.html']+=b'change';(tmp_path/'decision.zip').write_bytes(repack(files))
    bad=subprocess.run([sys.executable,'-I',str(tmp_path/'verify.py'),str(tmp_path/'decision.zip')],capture_output=True,text=True,cwd=tmp_path)
    assert bad.returncode==1 and not json.loads(bad.stdout)['valid']


def test_rehashed_source_file_still_must_match_original():
    module=exporter();files=unpack(module.build_package(snapshot()))
    source=next(n for n in files if n.startswith('sources/'))
    files[source]=b'Unrelated replacement document'
    result=module.verify_package(repack(files,True))
    assert not result['valid'] and any('source body' in e.lower() for e in result['errors'])


def test_rehashed_csv_cannot_reintroduce_a_formula():
    module=exporter();files=unpack(module.build_package(snapshot()))
    files['evidence.csv']=files['evidence.csv'].replace(b"'=old",b'=old')
    result=module.verify_package(repack(files,True))
    assert not result['valid'] and any('csv' in e.lower() for e in result['errors'])


def test_corrupt_deflate_stream_returns_invalid_instead_of_crashing():
    import struct
    module=exporter();payload=bytearray(module.build_package(snapshot()))
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        info=z.getinfo('decision.json')
    name_length,extra_length=struct.unpack_from('<HH',payload,info.header_offset+26)
    start=info.header_offset+30+name_length+extra_length
    payload[start:start+8]=b'\xff'*8
    assert not module.verify_package(bytes(payload))['valid']


def test_unexpected_session_fields_refuse_export():
    module=exporter();snap=snapshot()
    snap['record']['inputs']['session']={'csrf':'do-not-export'}
    snap['digest']=hashlib.sha256(canonical(snap['record'])).hexdigest()
    with pytest.raises(ValueError,match='input'):
        module.build_package(snap)
