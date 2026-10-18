"""SQLite revision store. Every mutation checks revision while holding the write lock."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import uuid
from .engine import evaluate
from .ingest import canonical,digest
from .costs import DEFAULTS
from .scoring import PROFILES

class Conflict(Exception):pass
class Forbidden(Exception):pass
class Invalid(Exception):pass


def now():return datetime.now(timezone.utc).isoformat()


def analysis_inputs(inputs):
    return {k:v for k,v in inputs.items() if k not in {'available_amendments','requirements_versions'}}


class Store:
    def __init__(self,path,inputs):
        self.path=str(path)
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO workspace VALUES (1,?)',(canonical(dict(revision=0,inputs=inputs,assumptions=DEFAULTS,profile='balanced',as_of='2026-10-17',reviews={},changes=[])),))

    def connect(self):
        db=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        return db

    def read(self,db):return json.loads(db.execute('SELECT body FROM workspace WHERE id=1').fetchone()['body'])
    def save(self,db,state):db.execute('UPDATE workspace SET body=? WHERE id=1',(canonical(state),))
    def evaluated(self,state):return evaluate(state['inputs'],state['assumptions'],state['profile'],state['as_of'],state['reviews'])

    @contextmanager
    def transaction(self,actor,required,revision):
        if actor!=required:raise Forbidden(f'This action requires the {required} role.')
        db=self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            state=self.read(db)
            if state['revision']!=revision:raise Conflict('Inputs changed. Reload the workbench and review the current revision.')
            yield db,state
            db.commit()
        except Exception:
            db.rollback();raise
        finally:db.close()

    def envelope(self,snapshot,state):
        snapshot=deepcopy(snapshot)
        snapshot['current']=snapshot['revision']==state['revision']
        snapshot['status']='stale' if not snapshot['current'] else ('approved' if snapshot.get('approval') else 'reviewed' if snapshot.get('review') else 'draft')
        return snapshot

    def state(self):
        with self.connect() as db:
            db.execute('BEGIN')
            s=self.read(db)
            snaps=[self.envelope(json.loads(x['body']),s) for x in db.execute('SELECT body FROM snapshots ORDER BY rowid DESC')]
            db.commit()
        return dict(revision=s['revision'],requirements_version=s['inputs']['requirements_version'],applied_amendments=s['inputs']['applied_amendments'],
            available_amendments=[{k:v for k,v in a.items() if k!='documents'} for a in s['inputs']['available_amendments']],
            assumptions=s['assumptions'],profile=s['profile'],as_of=s['as_of'],evaluation=self.evaluated(s),snapshots=snaps,changes=s['changes'])

    def changed(self,db,state,before,reason):
        state['revision']+=1
        after=self.evaluated(state)
        previous={p['id']:p for p in before['packages']}
        diffs=[]
        for p in after['packages']:
            old=previous[p['id']]
            aa={a['requirement_id']:a for a in old['assessments']}
            for a in p['assessments']:
                b=aa.get(a['requirement_id'])
                if not b or a!=b:
                    diffs.append(dict(package_id=p['id'],requirement_id=a['requirement_id'],before=b['state'] if b else 'absent',after=a['state'],reason=a['reason']))
            old_issues={a['id']:a for a in old['assurance']}
            new_issues={a['id']:a for a in p['assurance']}
            for key in sorted(old_issues.keys()|new_issues.keys()):
                a=old_issues.get(key);b=new_issues.get(key)
                if a!=b:
                    diffs.append(dict(package_id=p['id'],requirement_id='assurance:'+key,
                        before=a['disposition'] if a else 'absent',after=b['disposition'] if b else 'absent',
                        reason=b['reason'] if b else 'Issue no longer appears in the bounded matching set; this is not evidence of remediation.'))
            if p['cost']!=old['cost']:
                diffs.append(dict(package_id=p['id'],requirement_id='cost',before=old['cost']['known_total'],after=p['cost']['known_total'],reason='Cost inputs or planning assumptions changed.'))
            if p['score']!=old['score']:
                diffs.append(dict(package_id=p['id'],requirement_id='score',before=old['score']['low'],after=p['score']['low'],reason='Scoring evidence or preference weights changed.'))
        state['changes'].append({'revision':state['revision'],'at':now(),'reason':reason,'diffs':diffs,
            'approval_effect':'All previous snapshots are conservatively stale because the input revision changed. Re-review is required.'})
        self.save(db,state)

    def amend(self,actor,revision,id):
        with self.transaction(actor,'analyst',revision) as (db,s):
            a=next((a for a in s['inputs']['available_amendments'] if a['id']==id),None)
            if not a:raise Invalid('Unknown amendment')
            if id in s['inputs']['applied_amendments']:raise Invalid('Amendment already applied')
            before=self.evaluated(s)
            s['inputs']['documents'].extend(deepcopy(a['documents']))
            s['inputs']['documents'].sort(key=lambda d:d['id'])
            s['inputs']['applied_amendments'].append(id)
            self.changed(db,s,before,'Supplier amendment '+id+': '+a['title'])
        return self.state()

    def settings(self,actor,revision,requirements_version=None,profile=None,assumptions=None):
        with self.transaction(actor,'analyst',revision) as (db,s):
            before=self.evaluated(s)
            if requirements_version:
                if requirements_version not in s['inputs']['requirements_versions']:raise Invalid('Unknown requirements version')
                s['inputs']['requirements_version']=requirements_version
                s['inputs']['requirements']=s['inputs']['requirements_versions'][requirements_version]
            if profile:
                if profile not in PROFILES:raise Invalid('Unknown preference profile')
                s['profile']=profile
            if assumptions is not None:
                if set(assumptions)-set(DEFAULTS):raise Invalid('Unknown assumption field')
                merged=dict(s['assumptions'],**assumptions)
                if type(merged['years']) is not int or not 1<=merged['years']<=10:raise Invalid('Horizon must be an integer from 1 to 10 years')
                x=merged['replacements_per_aircraft_per_year']
                if type(x) not in {int,float} or not 0<=x<=10:raise Invalid('Replacement rate must be between 0 and 10')
                if type(merged['include_optional']) is not bool:raise Invalid('Optional selection must be boolean')
                s['assumptions']=merged
            self.changed(db,s,before,'Buyer policy, preference profile or explicit cost assumptions updated.')
        return self.state()

    def upload(self,actor,revision,filename,content,package_id,title):
        import re
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,100}\.(?:md|txt)',filename) or '..' in filename:
            raise Invalid('Use a plain .md or .txt filename. Archives and paths are not accepted.')
        if not content or len(content.encode())>102400 or '\x00' in content or any(ord(c)<32 and c not in '\n\r\t' for c in content):
            raise Invalid('Source must be nonempty UTF-8 text up to 100 KiB without binary control characters.')
        with self.transaction(actor,'analyst',revision) as (db,s):
            package=next((p for p in s['inputs']['packages'] if p['id']==package_id),None)
            if not package:raise Invalid('Unknown configuration')
            before=self.evaluated(s)
            id='UPLOAD-'+uuid.uuid4().hex[:12]
            s['inputs']['documents'].append(dict(id=id,package_id=package_id,supplier_id=package['supplier_id'],
                version=1,kind='clarification',path=filename,title=title,issued=s['as_of'],supersedes=[],layout='uploaded',content=content,hash=digest(content)))
            self.changed(db,s,before,'Additional inert document imported: '+id)
        return self.state()

    def snapshot(self,actor,revision,package_id,decision,rationale):
        with self.transaction(actor,'analyst',revision) as (db,s):
            e=self.evaluated(s)
            p=next((p for p in e['packages'] if p['id']==package_id),None)
            if not p:raise Invalid('Unknown configuration')
            if decision not in {'conditional','eligible'}:raise Invalid('Unknown decision type')
            if decision=='eligible' and not p['eligible']:raise Invalid('Mandatory gates remain open. Only a conditional decision can be recorded.')
            if not rationale.strip():raise Invalid('A decision rationale is required')
            record=dict(schema_version='1.0',application_version='0.1.0',created_at=now(),revision=s['revision'],
                inputs=analysis_inputs(s['inputs']),assumptions=s['assumptions'],profile=s['profile'],as_of=s['as_of'],reviews=s['reviews'],
                evaluation=e,package_id=package_id,decision=decision,rationale=rationale,limitations=e['limitations'])
            snapshot=dict(id='DEC-'+uuid.uuid4().hex[:10],digest=digest(record),revision=s['revision'],record=record,review=None,approval=None,history=[])
            db.execute('INSERT INTO snapshots VALUES (?,?)',(snapshot['id'],canonical(snapshot)))
            return self.envelope(snapshot,s)

    def get_stored(self,db,id):
        row=db.execute('SELECT body FROM snapshots WHERE id=?',(id,)).fetchone()
        if not row:raise Invalid('Unknown decision snapshot')
        return json.loads(row['body'])

    def check_current(self,snap,state):
        if snap['revision']!=state['revision']:raise Conflict('Snapshot is stale. Create and review a new snapshot.')
        if digest(snap['record'])!=snap['digest']:raise Invalid('Snapshot integrity mismatch')
        if snap['record']['inputs']!=analysis_inputs(state['inputs']):raise Conflict('Snapshot inputs do not match current inputs')

    def review(self,actor,revision,id,note):
        with self.transaction(actor,'reviewer',revision) as (db,s):
            snap=self.get_stored(db,id);self.check_current(snap,s)
            snap['review']=dict(role=actor,at=now(),note=note,digest=snap['digest'])
            snap['approval']=None
            snap['history'].append(dict(action='technical_review',**snap['review']))
            db.execute('UPDATE snapshots SET body=? WHERE id=?',(canonical(snap),id))
            return self.envelope(snap,s)

    def approve(self,actor,revision,id,note):
        with self.transaction(actor,'approver',revision) as (db,s):
            snap=self.get_stored(db,id);self.check_current(snap,s)
            if not snap.get('review') or snap['review']['digest']!=snap['digest']:raise Invalid('Current technical review is required before approval')
            snap['approval']=dict(role=actor,at=now(),note=note,digest=snap['digest'])
            snap['history'].append(dict(action='approval',**snap['approval']))
            db.execute('UPDATE snapshots SET body=? WHERE id=?',(canonical(snap),id))
            return self.envelope(snap,s)

    def get_snapshot(self,id):
        with self.connect() as db:
            db.execute('BEGIN');s=self.read(db);snap=self.get_stored(db,id);db.commit()
        return self.envelope(snap,s)

    def review_assertion(self,actor,revision,id,status,note):
        if status not in {'accepted','rejected'}:raise Invalid('Review must accept or reject interpretation')
        with self.transaction(actor,'reviewer',revision) as (db,s):
            before=self.evaluated(s)
            if not any(a['id']==id for a in before['assertions']):raise Invalid('Unknown assertion')
            s['reviews'][id]=dict(status=status,note=note,role=actor,at=now())
            self.changed(db,s,before,'Technical interpretation review of assertion '+id)
        return self.state()
