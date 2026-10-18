import json,socket,subprocess,os
from pathlib import Path
from failsafelab.runner import ROOT,limits
r=json.loads((ROOT/'evidence/development/baseline-01/run.json').read_text())
s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',5760));s.listen(1)
subprocess.run(['gdb','-batch','-ex','set debuginfod enabled off','-ex','run','-ex','bt','--args',*r['command']],cwd=ROOT/'evidence/development/startup-debug',preexec_fn=limits,timeout=12)
