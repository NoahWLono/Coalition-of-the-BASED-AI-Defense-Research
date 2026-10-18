"""Re-evaluate an exported record using this repository's pinned engine."""
import json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cedar.export import verify_package
from cedar.engine import evaluate

def reproduce(path):
    data=Path(path).read_bytes();verified=verify_package(data)
    if not verified['valid']:raise ValueError(verified['errors'])
    with zipfile.ZipFile(path) as z:r=json.loads(z.read('decision.json'))['record']
    result=evaluate(r['inputs'],r['assumptions'],r['profile'],r['as_of'],r['reviews'])
    return result==r['evaluation']

if __name__=='__main__':
    passed=reproduce(sys.argv[1]);print(json.dumps({'reproduced':passed,'package':sys.argv[1]}));sys.exit(0 if passed else 1)
