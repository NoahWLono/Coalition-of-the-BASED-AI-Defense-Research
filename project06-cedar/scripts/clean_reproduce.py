"""Exercise the released source in a new directory and virtual environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timezone
import urllib.request
import zipfile

from release import verify_release

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(root):
    files=[]
    for name in ['cedar','scripts','tests','data','vendor','evaluation']:
        files.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files.extend(root/n for n in ['pyproject.toml','uv.lock','.python-version'])
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    return hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def run(archive):
    archive=archive.resolve(); start=time.perf_counter(); report={'started_at':datetime.now(timezone.utc).isoformat(),'host_platform':platform.platform(),
        'tested_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'scope':'New temporary directory and new virtual environment on the same Linux host. uv dependency cache and installed managed Python may be reused. No independent-machine claim.','steps':[]}
    checked=verify_release(archive)
    if not checked['valid']:raise RuntimeError(checked)
    log=[]
    with tempfile.TemporaryDirectory(prefix='cedar-clean-') as temp:
        # The separately trusted release verifier has already checked all paths/types.
        with zipfile.ZipFile(archive) as z:z.extractall(temp)
        root=Path(temp)/'cedar'; report['functional_tree_sha256']=fingerprint(root)
        env=os.environ.copy();env.pop('VIRTUAL_ENV',None);env.pop('UV_PROJECT_ENVIRONMENT',None)
        def command(args):
            now=time.perf_counter(); result=subprocess.run(args,cwd=root,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
            log.append('$ '+' '.join(args)+'\n'+result.stdout)
            report['steps'].append({'command':args,'exit_code':result.returncode,'seconds':round(time.perf_counter()-now,3)})
            if result.returncode:raise RuntimeError(result.stdout)
            return result.stdout
        assert not (root/'.venv').exists()
        command(['uv','sync','--frozen'])
        before={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['data','evaluation'] for p in (root/folder).rglob('*') if p.is_file()}
        command(['uv','run','--frozen','python','-m','cedar','corpus'])
        after={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['data','evaluation'] for p in (root/folder).rglob('*') if p.is_file()}
        report['corpus_rebuild_byte_identical']=before==after
        if before!=after:raise RuntimeError('Rebuilt corpus differs from released corpus')
        command(['uv','run','--frozen','python','-m','cedar','verify'])
        command(['uv','run','--frozen','python','-m','cedar','walkthrough'])
        command(['uv','run','--frozen','python','scripts/verify_package.py','artifacts/full-decision.zip'])
        command(['uv','run','--frozen','python','scripts/reproduce_decision.py','artifacts/full-decision.zip'])
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        with (root/'artifacts/fresh-server.log').open('w') as server_log:
            server=subprocess.Popen([str(root/'.venv/bin/python'),'-m','cedar','demo','--port',str(port),'--db','runtime/fresh.sqlite'],cwd=root,env=env,stdout=server_log,stderr=server_log)
            try:
                for _ in range(100):
                    try:
                        health=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=.5));break
                    except Exception:time.sleep(.1)
                else:raise RuntimeError('Fresh server did not start')
                state=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/state'))
                html=urllib.request.urlopen(f'http://127.0.0.1:{port}/').read().decode()
                docs=urllib.request.urlopen(f'http://127.0.0.1:{port}/api/docs').read().decode()
                assert len(state['evaluation']['packages'])==12 and len(state['evaluation']['requirements'])==40
                assert 'CEDAR' in html and 'cdn.' not in docs
                report['fresh_server']={'health':health,'packages':12,'requirements':40,'home_http':200,'offline_api_reference_http':200}
            finally:server.terminate();server.wait(timeout=10)
        report['evaluation']=json.loads((root/'artifacts/evaluation.json').read_text())
    report.update(passed=True,duration_seconds=round(time.perf_counter()-start,3),finished_at=datetime.now(timezone.utc).isoformat())
    (ROOT/'artifacts/clean-reproduction.log').write_text('\n\n'.join(log))
    (ROOT/'artifacts/clean-reproduction.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'evaluation','steps'}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',nargs='?',type=Path,default=ROOT/'dist/cedar-portfolio-source.zip')
    run(parser.parse_args().archive)
