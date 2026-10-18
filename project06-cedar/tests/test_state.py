from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io,json,zipfile
import pytest
from cedar.store import Store, Conflict, Forbidden, Invalid
from cedar.ingest import digest
from cedar.export import build_package, verify_package
from test_engine import doc,row,req


def inputs():
    d=doc(row());d.update(title='Synthetic document',path='source.md',hash=digest(d['content']))
    return dict(schema_version='1.0',suppliers=[{'id':'s1','name':'Synthetic'}],packages=[{'id':'p1','supplier_id':'s1','name':'Sample'}],
        requirements=[req()],requirements_versions={'v1':[req()]},requirements_version='v1',documents=[d],structured={},
        applied_amendments=[],available_amendments=[{'id':'AMD01','title':'Reduced quantity','documents':[dict(doc(row(value='2'),'d2'),supersedes=['d1'])]}])


def test_roles_stale_snapshot_and_portable_export(tmp_path):
    s=Store(tmp_path/'db',inputs())
    snap=s.snapshot('analyst',0,'p1','eligible','Documentary consideration only')
    with pytest.raises(Forbidden): s.approve('analyst',0,snap['id'],'No')
    with pytest.raises(Invalid): s.approve('approver',0,snap['id'],'No review')
    s.review('reviewer',0,snap['id'],'Checked citations')
    s.approve('approver',0,snap['id'],'Approved for consideration')
    assert s.state()['snapshots'][0]['status']=='approved'
    s.amend('analyst',0,'AMD01')
    assert s.state()['snapshots'][0]['status']=='stale'
    assert not s.state()['evaluation']['packages'][0]['eligible']
    with pytest.raises(Conflict):s.approve('approver',0,snap['id'],'Old revision')
    with pytest.raises(Invalid):s.snapshot('analyst',1,'p1','eligible','Cannot pass')
    package=build_package(s.get_snapshot(snap['id']))
    assert verify_package(package)['valid']
    z=zipfile.ZipFile(io.BytesIO(package)); files={n:z.read(n) for n in z.namelist()}
    files['report.html']+=b'tampered'
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as out:
        for n,b in files.items():out.writestr(n,b)
    assert not verify_package(buf.getvalue())['valid']


def test_concurrent_amendments_have_one_winner(tmp_path):
    s=Store(tmp_path/'db',inputs())
    def change():
        try:s.amend('analyst',0,'AMD01');return 'ok'
        except Conflict:return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _:change(),range(2)))==['conflict','ok']
    assert s.state()['revision']==1


def test_racing_approval_and_amendment_never_approve_current_old_data(tmp_path):
    s=Store(tmp_path/'db',inputs());snap=s.snapshot('analyst',0,'p1','eligible','Consider')
    s.review('reviewer',0,snap['id'],'Evidence read')
    def approve():
        try:s.approve('approver',0,snap['id'],'Consider');return 'approved'
        except Conflict:return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(approve);b=pool.submit(s.amend,'analyst',0,'AMD01');a.result();b.result()
    assert s.state()['snapshots'][0]['status']=='stale'


def test_rejection_invalidates_support_and_records_reason(tmp_path):
    s=Store(tmp_path/'db',inputs()); aid=s.state()['evaluation']['assertions'][0]['id']
    s.review_assertion('reviewer',0,aid,'rejected','Quantity not credible')
    state=s.state()
    assert state['evaluation']['packages'][0]['assessments'][0]['state']=='unresolved'
    assert state['evaluation']['assertions'][0]['review']['note']=='Quantity not credible'
