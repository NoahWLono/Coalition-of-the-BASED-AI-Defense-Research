"""Loopback-only synthetic demonstration API with server-enforced role permissions."""
from pathlib import Path
import hmac
import os
import secrets
import time
from typing import Literal
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field
from .ingest import load_corpus
from .store import Store, Conflict, Forbidden, Invalid
from .export import build_package

ROOT=Path(__file__).resolve().parent.parent

class StrictModel(BaseModel):model_config=ConfigDict(extra='forbid')
class Login(StrictModel):
    role:Literal['analyst','reviewer','approver']
    password:str=Field(max_length=100)
class Revision(StrictModel):expected_revision:int=Field(ge=0)
class Settings(Revision):
    requirements_version:Literal['v1','v2']|None=None
    profile:Literal['balanced','operations','support']|None=None
    assumptions:dict|None=None
class Amendment(Revision):id:str=Field(max_length=100)
class Upload(Revision):
    filename:str=Field(max_length=120)
    content:str=Field(max_length=102400)
    package_id:str=Field(max_length=80)
    title:str=Field(min_length=1,max_length=200)
class Snapshot(Revision):
    package_id:str=Field(max_length=80)
    decision:Literal['eligible','conditional']
    rationale:str=Field(min_length=1,max_length=4000)
class Review(Revision):note:str=Field(min_length=1,max_length=4000)
class AssertionReview(Review):status:Literal['accepted','rejected']


def create_app(store=None,test_mode=False):
    if store is None:
        corpus=Path(os.environ.get('CEDAR_CORPUS',str(ROOT/'data/full')))
        store=Store(os.environ.get('CEDAR_DB',str(ROOT/'runtime/cedar.sqlite')),load_corpus(corpus))
    app=FastAPI(title='CEDAR synthetic procurement workbench',version='0.1.0',docs_url=None,redoc_url=None)
    app.state.store=store
    sessions={}
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','[::1]']+(['testserver'] if test_mode else []))

    @app.middleware('http')
    async def boundaries(request:Request,call_next):
        if request.method not in {'GET','HEAD','OPTIONS'}:
            origin=request.headers.get('origin')
            if origin and origin!=str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'Cross-origin writes are not accepted.'},403)
            data=b''
            async for part in request.stream():
                data+=part
                if len(data)>250000:return JSONResponse({'detail':'Request exceeds 250 KB limit.'},413)
            request._body=data
        response=await call_next(request)
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store'
        return response

    @app.exception_handler(Conflict)
    async def conflict(request,error):return JSONResponse({'detail':str(error)},409)
    @app.exception_handler(Forbidden)
    async def forbidden(request,error):return JSONResponse({'detail':str(error)},403)
    @app.exception_handler(Invalid)
    async def invalid(request,error):return JSONResponse({'detail':str(error)},422)

    def session(request,write=False):
        s=sessions.get(request.cookies.get('cedar_session'))
        if not s or s['expires']<time.time():raise HTTPException(401,'Sign in using a demonstration role.')
        if write and not hmac.compare_digest(request.headers.get('x-csrf-token',''),s['csrf']):
            raise HTTPException(403,'Missing or invalid session write token. Sign in again.')
        return s
    def actor(request):return session(request,True)['role']

    @app.post('/api/login')
    def login(body:Login,request:Request):
        if not hmac.compare_digest(body.password,'cedar-'+body.role):raise HTTPException(401,'Incorrect demonstration password.')
        sessions.pop(request.cookies.get('cedar_session'),None)
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        sessions[token]={'role':body.role,'csrf':csrf,'expires':time.time()+8*3600}
        response=JSONResponse({'role':body.role,'csrf':csrf})
        response.set_cookie('cedar_session',token,httponly=True,samesite='strict',max_age=8*3600)
        return response

    @app.get('/api/session')
    def me(request:Request):
        s=session(request);return {'role':s['role'],'csrf':s['csrf']}

    @app.get('/api/state')
    def state(request:Request):
        result=store.state()
        s=sessions.get(request.cookies.get('cedar_session'),{})
        result['role']=s.get('role') if s.get('expires',0)>time.time() else None
        return result

    @app.post('/api/settings')
    def settings(body:Settings,request:Request):
        return store.settings(actor(request),body.expected_revision,body.requirements_version,body.profile,body.assumptions)

    @app.post('/api/amendments')
    def amend(body:Amendment,request:Request):return store.amend(actor(request),body.expected_revision,body.id)

    @app.post('/api/uploads')
    def upload(body:Upload,request:Request):return store.upload(actor(request),**{'revision' if k=='expected_revision' else k:v for k,v in body.model_dump().items()})

    @app.post('/api/snapshots')
    def snapshot(body:Snapshot,request:Request):return store.snapshot(actor(request),body.expected_revision,body.package_id,body.decision,body.rationale)

    @app.post('/api/snapshots/{id}/review')
    def review(id:str,body:Review,request:Request):return store.review(actor(request),body.expected_revision,id,body.note)

    @app.post('/api/snapshots/{id}/approve')
    def approve(id:str,body:Review,request:Request):return store.approve(actor(request),body.expected_revision,id,body.note)

    @app.post('/api/assertions/{id}/review')
    def assertion_review(id:str,body:AssertionReview,request:Request):
        return store.review_assertion(actor(request),body.expected_revision,id,body.status,body.note)

    @app.get('/api/documents/{id}')
    def document(id:str):
        with store.connect() as db:inputs=store.read(db)['inputs']
        d=next((d for d in inputs['documents'] if d['id']==id),None)
        if not d:raise HTTPException(404,'Source version not found')
        return d

    @app.get('/api/export/{id}')
    def export(id:str):
        data=build_package(store.get_snapshot(id))
        return Response(data,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="cedar-{id}.zip"'})

    @app.get('/api/docs', response_class=HTMLResponse)
    def api_reference():
        return '<!doctype html><html lang="en"><meta charset="utf-8"><title>CEDAR API reference</title><link rel="stylesheet" href="/static/style.css"><main style="max-width:900px;margin:50px auto;padding:30px"><h1>CEDAR API reference</h1><p>Local synthetic workbench. Read the <a href="/openapi.json">complete OpenAPI schema</a> or return to the <a href="/">workbench</a>.</p><h2>Reads</h2><p>GET /api/state, /api/documents/{id}, /api/export/{id}, /api/health.</p><h2>Session</h2><p>POST /api/login with role and demonstration password. Send the returned X-CSRF-Token header and session cookie for every write.</p><h2>Analyst</h2><p>POST /api/settings, /api/uploads, /api/amendments, /api/snapshots.</p><h2>Technical reviewer</h2><p>POST /api/assertions/{id}/review and /api/snapshots/{id}/review.</p><h2>Approver</h2><p>POST /api/snapshots/{id}/approve. A current technical review is required.</p><p>Every write includes expected_revision. Stale revisions return HTTP 409. Role violations return 403. All data and identities are synthetic demonstration fixtures.</p></main></html>'

    @app.get('/api/health')
    def health():return {'status':'ok','synthetic':True,'version':'0.1.0'}

    app.mount('/static',StaticFiles(directory=ROOT/'cedar/static'),name='static')
    @app.get('/')
    def index():return FileResponse(ROOT/'cedar/static/index.html')
    return app
