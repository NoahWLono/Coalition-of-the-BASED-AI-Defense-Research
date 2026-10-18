"""Small, Fish-compatible command entry point for the local workbench."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent


def main():
    ap=argparse.ArgumentParser(description='CEDAR synthetic procurement workbench')
    commands=ap.add_subparsers(dest='command',required=True)
    demo=commands.add_parser('demo',help='Launch local workbench; single CPU server')
    demo.add_argument('--port',type=int,default=8765)
    demo.add_argument('--db',type=Path,default=ROOT/'runtime/cedar.sqlite')
    demo.add_argument('--scope',choices=['slice','full'],default='full')
    commands.add_parser('corpus',help='Rebuild both synthetic corpora')
    commands.add_parser('verify',help='Run tests and measured corpus evaluation')
    commands.add_parser('walkthrough',help='Replay complete API demonstration into artifacts/')
    commands.add_parser('export',help='Build sample decision and complete repository release')
    args=ap.parse_args()
    os.chdir(ROOT)
    if args.command=='demo':
        os.environ['CEDAR_DB']=str(args.db.resolve())
        os.environ['CEDAR_CORPUS']=str(ROOT/'data'/args.scope)
        import uvicorn
        print('CEDAR synthetic demo: http://127.0.0.1:'+str(args.port)+' | one worker | no paid services')
        uvicorn.run('cedar.app:create_app',factory=True,host='127.0.0.1',port=args.port,workers=1,log_level='warning')
    elif args.command=='corpus':
        for scope in ['slice','full']:
            subprocess.run([sys.executable,'scripts/generate_corpus.py','--scope',scope],check=True)
    elif args.command=='verify':
        subprocess.run([sys.executable,'-m','pytest','-q'],check=True)
        subprocess.run([sys.executable,'scripts/evaluate.py'],check=True)
    elif args.command=='walkthrough':
        subprocess.run([sys.executable,'scripts/walkthrough.py'],check=True)
    elif args.command=='export':
        subprocess.run([sys.executable,'scripts/walkthrough.py'],check=True)
        subprocess.run([sys.executable,'scripts/release.py'],check=True)

if __name__=='__main__':main()
