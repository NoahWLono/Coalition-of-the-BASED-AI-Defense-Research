import argparse
import json
from pathlib import Path
from .acquire import acquire
from .reporting import build_report, synthetic_demo


def main():
    p=argparse.ArgumentParser(description='Conservative civilian paper comparability audit')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('acquire',help='Explicit bounded public GET acquisition, network required')
    a.add_argument('--root',type=Path,default=Path('.'));a.add_argument('--target',type=int,default=50);a.add_argument('--request-cap',type=int,default=150)
    r=sub.add_parser('report',help='Offline deterministic report from saved extracts')
    r.add_argument('--extract-dir',type=Path,default=Path('data/extracts'));r.add_argument('--output',type=Path,default=Path('output/real'))
    r.add_argument('--reviews',type=Path);r.add_argument('--labels',type=Path)
    d=sub.add_parser('demo',help='Clearly labeled synthetic algorithm fixture')
    d.add_argument('--output',type=Path,default=Path('output/synthetic'))
    args=p.parse_args()
    if args.command=='acquire':result=acquire(args.root,args.target,args.request_cap)
    elif args.command=='report':result=build_report(args.extract_dir,args.output,args.labels,args.reviews)
    else:result=synthetic_demo(args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))


if __name__=='__main__':main()
