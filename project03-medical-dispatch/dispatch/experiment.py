"""Bounded reproducible experiment runner; all written schedules are checked."""
import argparse
import copy
import csv
import hashlib
import json
import platform
import shlex
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import importlib.metadata
from .generate import benchmark, sensitivity_cases
from .simulate import simulate
from .optimize import optimize, online_optimize
from .checker import validate_schedule
from .metrics import summarize
from .reference import exhaustive


def write_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def capacity_certificate(out):
    """An extra charger preserves every operation in the one-charger schedule."""
    s=json.loads((out/'scenarios'/'chargers_2.json').read_text())
    a=copy.deepcopy(json.loads((out/'schedules'/'baseline__offline__milp.json').read_text()))
    raw=json.loads((out/'schedules'/'chargers_2__offline__milp.json').read_text())
    a.update(scenario_id=s['id'],policy='capacity_transfer')
    objective=summarize(s,a)['objective']
    lower=raw['solver']['lower_bound']
    a['solver']=dict(status='TRANSFERRED_FEASIBLE',optimal=False,lower_bound=lower,
                     relative_gap=max(0,objective-lower)/max(abs(objective),1e-12),
                     feasible_objective=objective,source='baseline__offline__milp.json',
                     bound_source='chargers_2__offline__milp.json',
                     bound_scope='two_charger_integer_slot_problem')
    record(out,'chargers_2_transfer',s,a)
    certificate=dict(objective=objective,lower_bound=lower,relative_gap=a['solver']['relative_gap'],
                     source='baseline__offline__milp.json',schedule='chargers_2_transfer__offline__capacity_transfer.json',
                     valid=True,explanation='Adding an unused charger preserves all source operations.')
    write_json(out/'capacity_certificate.json',certificate)
    return certificate


def record(out, name, s, schedule):
    errors=validate_schedule(s,schedule)
    if errors:
        write_json(out/'invalid'/f'{name}.json',dict(scenario=s,schedule=schedule,errors=errors))
        raise RuntimeError(f'Independent validation failed: {name}: {errors}')
    metrics=summarize(s,schedule)
    stem=f"{name}__{schedule['information']}__{schedule['policy']}"
    write_json(out/'scenarios'/f'{name}.json',s)
    write_json(out/'schedules'/f'{stem}.json',schedule)
    write_csv(out/'schedules'/f'{stem}_services.csv',schedule['services'])
    write_csv(out/'schedules'/f'{stem}_charges.csv',schedule['charges'])
    write_csv(out/'schedules'/f'{stem}_unserved.csv',schedule['unserved'])
    write_json(out/'validation'/f'{stem}.json',dict(valid=True,errors=[],checker='dispatch.checker',
               scenario=name,policy=schedule['policy'],information=schedule['information']))
    write_json(out/'metrics'/f'{stem}.json',metrics)
    row={k:v for k,v in metrics.items() if not isinstance(v,dict)}
    row['case']=name
    solver=schedule['solver']
    row.update(solver_status=solver.get('status','rolling'),
               optimal=solver.get('optimal',False), lower_bound=solver.get('lower_bound'),
               relative_gap=solver.get('relative_gap'),
               used_fallback=solver.get('used_fallback',False))
    return row,metrics


def plot(out,rows,details):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'#fafaf7',
                         'axes.facecolor':'#fafaf7','axes.spines.top':False,'axes.spines.right':False})
    colors={'fcfs':'#c46b32','edf':'#277b87','milp':'#293b68','rolling_milp':'#7865aa'}
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    base=[r for r in rows if r['case']=='baseline']
    labels=[f"{r['information']}\n{r['policy']}" for r in base]
    for ax,key,title in zip(axes.flat,['served','lateness_minutes','objective','charging_queue_peak'],
                             ['Requests served (19 eligible)','Total lateness among served (minutes)',
                              'Declared objective (lower is better)','Peak depleted batteries waiting']):
        ax.bar(labels,[r[key] for r in base],color=[colors[r['policy']] for r in base])
        ax.set_title(title,loc='left',fontweight='bold'); ax.tick_params(axis='x',labelsize=8)
        for i,r in enumerate(base): ax.text(i,r[key],f"{r[key]:.1f}",ha='center',va='bottom',fontsize=8)
    fig.suptitle('Synthetic medical-supply dispatch | seed 1801\nOffline and online are separate information regimes',fontweight='bold')
    fig.savefig(out/'figures'/'comparison.png',dpi=160); plt.close(fig)

    cases=list(dict.fromkeys(r['case'] for r in rows if r['information']=='offline'))
    fig,axes=plt.subplots(1,3,figsize=(14,6),layout='constrained')
    for ax,key,title in zip(axes,['served','lateness_minutes','maximum_regional_rejection_fraction'],
                            ['Requests served','Total served lateness (min)','Worst regional rejection fraction']):
        for j,policy in enumerate(('fcfs','edf','milp')):
            data=[next(r for r in rows if r['case']==c and r['policy']==policy and r['information']=='offline') for c in cases]
            ax.barh(np.arange(len(cases))+(j-1)*.24,[r[key] for r in data],height=.22,label=policy,color=colors[policy])
        limited={r['case'] for r in rows if r['policy']=='milp' and not r['optimal']}
        ax.set_yticks(range(len(cases)),[c+' *' if c in limited else c for c in cases]); ax.invert_yaxis(); ax.set_title(title,loc='left'); ax.legend(fontsize=8)
    fig.suptitle('One-factor sensitivity | identical paired fixtures within each row\n* Time-limited MILP incumbent; no optimal capacity comparison for that row',fontweight='bold')
    fig.savefig(out/'figures'/'sensitivity.png',dpi=160); plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for ax,dimension in zip(axes,('region','category')):
        names=sorted(next(m for m in details if m['scenario_id']==benchmark()['id'])['distributions'][dimension])
        grid=[]
        for r in base:
            m=next(m for m in details if m['scenario_id']==r['scenario_id'] and m['policy']==r['policy'] and m['information']==r['information'])
            grid.append([m['distributions'][dimension][n]['service_rate'] for n in names])
        ax.imshow(grid,vmin=0,vmax=1,cmap='YlGnBu',aspect='auto')
        ax.set_xticks(range(len(names)),names); ax.set_yticks(range(len(base)),[x.replace('\n',' ') for x in labels]); ax.set_title(dimension.title()+' service fraction')
        for i,row in enumerate(grid):
            for j,value in enumerate(row): ax.text(j,i,f'{value:.0%}',ha='center',va='center',color='white' if value>.6 else 'black')
    fig.suptitle('Distribution checks | cancelled requests excluded',fontweight='bold')
    fig.savefig(out/'figures'/'fairness.png',dpi=160); plt.close(fig)

    schedule=json.loads((out/'schedules'/'baseline__offline__milp.json').read_text())
    s=json.loads((out/'scenarios'/'baseline.json').read_text())
    resources=[v['id'] for v in s['vehicles']]+s['charger_ids']+s['technician_ids']
    fig,ax=plt.subplots(figsize=(13,5),layout='constrained')
    for a in schedule['services']:
        y=resources.index(a['vehicle_id']); ax.broken_barh([(a['start']*5,(a['end']-a['start'])*5)],(y-.3,.6),facecolors=colors['milp'])
        ax.text((a['start']+a['end'])*2.5,y,a['request_id'],ha='center',va='center',fontsize=7,color='white')
        ax.broken_barh([(a['start']*5,s['load_time']*5)],(resources.index(a['technician_id'])-.3,.6),facecolors=colors['milp'])
    for c in schedule['charges']:
        for resource in (c['charger_id'],c['technician_id']):
            ax.broken_barh([(c['start']*5,(c['end']-c['start'])*5)],(resources.index(resource)-.3,.6),facecolors='#52a39c')
    for v in s['vehicles']:
        for a,b in v['unavailable']:
            ax.broken_barh([(a*5,(b-a)*5)],(resources.index(v['id'])-.4,.8),facecolors='#e9b1ad',hatch='//')
    ax.set_yticks(range(len(resources)),resources); ax.set_xlabel('Minutes from synthetic shift start'); ax.set_xlim(0,s['horizon']*5)
    ax.set_title('Baseline offline MILP schedule | blue service, teal charge, hatched unavailable',loc='left',fontweight='bold')
    fig.savefig(out/'figures'/'schedule.png',dpi=160); plt.close(fig)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=Path('results'))
    parser.add_argument('--offline-limit',type=float,default=3)
    parser.add_argument('--online-limit',type=float,default=.5)
    args=parser.parse_args()
    out=args.out
    for folder in ('figures','schedules','scenarios','metrics','validation'):
        (out/folder).mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    rows,details=[],[]
    for name,s in sensitivity_cases(benchmark()):
        for policy in ('fcfs','edf','milp'):
            schedule=optimize(s,time_limit=args.offline_limit) if policy=='milp' else simulate(s,policy,'offline')
            row,metrics=record(out,name,s,schedule); rows.append(row); details.append(metrics)
            print(f"{name} offline {policy}: served={row['served']}, rejected={row['rejected']}, objective={row['objective']:.3f}, bound={row['lower_bound']}",flush=True)
    s=benchmark()
    for policy in ('fcfs','edf','rolling_milp'):
        schedule=online_optimize(s,time_limit=args.online_limit) if policy=='rolling_milp' else simulate(s,policy,'online')
        row,metrics=record(out,'baseline',s,schedule); rows.append(row); details.append(metrics)
        print(f"baseline online {policy}: served={row['served']}, rejected={row['rejected']}, objective={row['objective']:.3f}",flush=True)
    tiny=[]
    from .tiny_cases import tiny_cases
    for name,s in tiny_cases():
        reference=exhaustive(s)
        optimized=optimize(s,time_limit=5)
        for a in (reference['schedule'],optimized):
            record(out,f'tiny_{name}',s,a)
        actual=summarize(s,optimized)['objective']
        assert optimized['solver']['optimal'] and abs(reference['objective']-actual)<1e-6
        tiny.append(dict(case=name,objective=actual,reference_objective=reference['objective'],
                         states=reference['enumerated_states'],transitions=reference['transitions'],
                         lower_bound=optimized['solver']['lower_bound'],status=optimized['solver']['status']))
    write_csv(out/'comparison.csv',rows); write_json(out/'comparison.json',rows)
    write_json(out/'tiny_agreement.json',tiny)
    distributions=[]
    for row,m in zip(rows,details):
        for dimension,groups in m['distributions'].items():
            for name,group in groups.items():
                distributions.append(dict(case=row['case'],information=m['information'],policy=m['policy'],dimension=dimension,group=name,**group))
    write_csv(out/'distributions.csv',distributions)
    capacity_certificate(out)
    plot(out,rows,details)
    import scipy.optimize._highspy._core as highs
    version=highs._Highs()
    metadata=dict(timestamp=datetime.now(ZoneInfo('America/Toronto')).isoformat(),
                  command=shlex.join([sys.executable,'-m','dispatch.experiment',*sys.argv[1:]]),
                  argv=[sys.executable,'-m','dispatch.experiment',*sys.argv[1:]],cwd=str(Path.cwd()),
                  python=sys.version,platform=platform.platform(),
                  packages={x:importlib.metadata.version(x) for x in ('scipy','numpy','matplotlib','pytest')},
                  highs_version=f'{version.versionMajor()}.{version.versionMinor()}.{version.versionPatch()}',
                  seed=1801,offline_time_limit=args.offline_limit,online_time_limit=args.online_limit,
                  elapsed_seconds=time.monotonic()-started,comparison_schedules=len(rows),tiny_cases=len(tiny),
                  transfer_certificates=1,
                  validated_schedules=len(list((out/'validation').glob('*.json'))))
    write_json(out/'run_metadata.json',metadata)
    from .report import generate_report
    generate_report(out)
    print(json.dumps(metadata,indent=2),flush=True)


if __name__=='__main__':
    main()
