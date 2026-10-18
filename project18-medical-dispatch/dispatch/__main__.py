"""Schedule one scenario and verify its exported result."""
import argparse
import json
from pathlib import Path
from .checker import validate_schedule
from .metrics import summarize
from .simulate import simulate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scenario',type=Path)
    p.add_argument('--policy',choices=['fcfs','edf','milp'],default='fcfs')
    p.add_argument('--information',choices=['offline','online'],default='offline')
    p.add_argument('--time-limit',type=float,default=3)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    s=json.loads(args.scenario.read_text())
    if args.policy=='milp':
        from .optimize import optimize,online_optimize
        a=(online_optimize if args.information=='online' else optimize)(s,time_limit=args.time_limit)
    else:
        a=simulate(s,args.policy,args.information)
    errors=validate_schedule(s,a)
    if errors:
        raise SystemExit('\n'.join(errors))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(a,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summarize(s,a),indent=2,allow_nan=False))


if __name__=='__main__':
    main()
