"""Bounded reproducible numerical audit against independent point sampling."""
import argparse
from collections import Counter, defaultdict
import html
import json
import math
from pathlib import Path
import platform
import time

from .reference import accepts, dense_grid
from .solver import contains, solve

ROOT = Path(__file__).resolve().parents[1]


def failure_counts(rows, supplemental, monotone, nested):
    checked = rows + supplemental
    return {'reference_points_missed': sum(r['reference_points_missed'] for r in checked),
            'valid_truth_exclusions': sum(r['truth_exact_accepted'] and not r['truth_outer_covered'] for r in checked),
            'inner_point_failures': sum(r['inner_point_failures'] for r in checked),
            'nonmonotone_added_cells': sum(r['added_cells'] for r in monotone),
            'non_nested_cells': sum(r['non_nested_cells'] for r in nested)}


def indices(result):
    return {(c[0], c[1]) for c in result['cells']}


def point_index(scene, point, n):
    a,b,c,d=scene['bounds']
    return min(n-1,math.floor((point[0]-a)*n/(c-a))),min(n-1,math.floor((point[1]-b)*n/(d-b)))


def audit_scene(scene, truth, n=128, reference_n=256):
    ids=scene['default_observations']
    result=solve(scene,n,ids)
    reference=dense_grid(scene,reference_n,ids)
    retained=indices(result)
    missed=[p for p in reference['points'] if point_index(scene,p,n) not in retained]
    a,b,_,_=scene['bounds'];dx=result['grid']['dx'];dy=result['grid']['dy']
    inner_checks=0; inner_failures=[]
    for ix,iy,inner,_ in result['cells']:
        if not inner: continue
        for ox,oy in [(0,0),(0,1),(1,0),(1,1),(.5,.5)]:
            point=[a+(ix+ox)*dx,b+(iy+oy)*dy];inner_checks+=1
            if not accepts(scene,point,ids): inner_failures.append(point)
    truth_valid=accepts(scene,truth['camera'],ids)
    truth_covered=contains(result,truth['camera'])
    ix,iy=point_index(scene,truth['camera'],n)
    center=[a+(ix+.5)*dx,b+(iy+.5)*dy]
    center_valid=accepts(scene,center,ids)
    if not truth_valid:
        classification='inconsistent evidence' if result['status']=='incompatible' else 'model violation at source camera'
    elif not truth_covered: classification='numerical truth exclusion'
    elif not result['center_witness_count']: classification='unresolved without center witness'
    else: classification='valid covered'
    row={'scene_id':scene['id'],'split':scene['split'],'resolution':n,'reference_resolution':reference_n,
         'truth_exact_accepted':truth_valid,'truth_outer_covered':truth_covered,
         'truth_cell_center_accepted':center_valid,'discretization_center_miss':truth_valid and not center_valid,
         'classification':classification,'status':result['status'],
         'area_lower':result['area_lower'],'area_upper':result['area_upper'],
         'area_bracket_width':result['area_uncertain'],'reference_sample_area':reference['area'],
         'reference_area_within_bracket':result['area_lower']-1e-10<=reference['area']<=result['area_upper']+1e-10,
         'reference_accepted_count':reference['accepted_count'],'reference_points_missed':len(missed),
         'inner_point_checks':inner_checks,'inner_point_failures':len(inner_failures),
         'outer_components':len(result['components']),
         'witnessed_components':sum(c['witness_count']>0 for c in result['components']),
         'unwitnessed_outer_components':sum(c['witness_count']==0 for c in result['components']),
         'components':result['components'],'solver_runtime_ms':result['runtime_ms'],
         'reference_runtime_ms':reference['runtime_ms']}
    return row


def monotonicity(scene,n=128):
    ids=scene['default_observations']; previous=None;checks=0;failures=0
    for length in range(1,len(ids)+1):
        current=indices(solve(scene,n,ids[:length]))
        if previous is not None:
            checks+=1; failures+=len(current-previous)
        previous=current
    return {'scene_id':scene['id'],'resolution':n,'prefix_comparisons':checks,'added_cells':failures}


def nesting(scene):
    results={n:indices(solve(scene,n,scene['default_observations'])) for n in (64,128,256)}
    return {'scene_id':scene['id'],'comparisons':2,
            'non_nested_cells':sum(sum((i//2,j//2) not in results[n//2] for i,j in results[n]) for n in (128,256))}


def teaching_svg(scenes,path):
    fragments=['<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="1120" viewBox="0 0 1240 1120">',
               '<rect width="1240" height="1120" fill="#f6f4ed"/><style>text{font-family:monospace;fill:#172e35}.small{font-size:11px}.note{font-size:12px}</style>',
               '<text x="28" y="28" font-size="20">Synthetic angle ambiguity and one-observation resolution</text>',
               '<text x="28" y="49" class="note">Same local coordinate scale in all panels. Angles alone preserve reflection across the landmark baseline.</text>']
    for number,(scene,truth) in enumerate(scenes):
        result=solve(scene,256,scene['default_observations'])
        ox=60+(number%2)*615;oy=100+(number//2)*480;scale=27
        def xy(p): return ox+(p[0]+8)*scale,oy+(7-p[1])*scale
        fragments.append(f'<text x="{ox}" y="{oy-26}" font-size="16">{html.escape(scene["title"])}</text>')
        fragments.append(f'<text x="{ox}" y="{oy-9}" class="small">Active: {", ".join(scene["default_observations"])}</text>')
        fragments.append(f'<rect x="{ox}" y="{oy}" width="432" height="378" fill="white" stroke="#a7b2af"/>')
        for tick in range(-8,9,2):
            x,_=xy([tick,0])
            fragments.append(f'<path d="M{x},{oy}v378" stroke="#e5ecec"/><text x="{x}" y="{oy+393}" text-anchor="middle" class="small">{tick}</text>')
        for tick in range(-6,7,2):
            _,y=xy([0,tick])
            fragments.append(f'<path d="M{ox},{y}h432" stroke="#e5ecec"/><text x="{ox-8}" y="{y+4}" text-anchor="end" class="small">{tick}</text>')
        _,baseline=xy([0,0])
        fragments.append(f'<path d="M{ox},{baseline}h432" stroke="#889c9e" stroke-dasharray="5 4"/><text x="{ox+435}" y="{baseline+4}" class="small">y=0</text>')
        fragments.append(f'<text x="{ox+216}" y="{oy+411}" text-anchor="middle" class="small">x (local metres)</text><text x="{ox-36}" y="{oy+180}" transform="rotate(-90 {ox-36} {oy+180})" text-anchor="middle" class="small">y (local metres)</text>')
        for ix,iy,inner,cid in result['cells']:
            x,y=xy([-8+ix*16/256,-7+(iy+1)*14/256])
            fragments.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="1.6875" height="1.4765625" fill="{"#23806d" if inner else "#eab66b"}"/>')
        for lm in scene['landmarks']:
            x,y=xy([lm['x'],lm['y']]);fragments.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#172e35"/><text x="{x+5}" y="{y-6}" class="small">{lm["id"]}</text>')
        camera=truth['camera'];x,y=xy(camera)
        fragments.append(f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="#b52e50" stroke-width="2"/><path d="M{x+7},{y-5}l24,-18" stroke="#b52e50"/><text x="{x+33}" y="{y-25}" class="small">source camera</text>')
        if number<2:
            rx,ry=xy([camera[0],-camera[1]])
            fragments.append(f'<path d="M{rx+6},{ry+5}l22,20" stroke="#687a7d"/><text x="{rx+30}" y="{ry+29}" class="small">reflected branch</text>')
        # A one-metre square inset makes inner cells visible without changing panel scale.
        zx,zy=ox+445,oy+10;size=100;cx,cy=camera
        fragments.append(f'<text x="{zx}" y="{zy-5}" class="small">1 m × 1 m</text><rect x="{zx}" y="{zy}" width="{size}" height="{size}" fill="white" stroke="#889c9e"/>')
        for ix,iy,inner,cid in result['cells']:
            left=-8+ix*16/256;right=left+16/256;bottom=-7+iy*14/256;top=bottom+14/256
            left=max(left,cx-.5);right=min(right,cx+.5);bottom=max(bottom,cy-.5);top=min(top,cy+.5)
            if left<right and bottom<top:
                fragments.append(f'<rect x="{zx+(left-cx+.5)*size:.3f}" y="{zy+(cy+.5-top)*size:.3f}" width="{(right-left)*size:.3f}" height="{(top-bottom)*size:.3f}" fill="{"#23806d" if inner else "#eab66b"}"/>')
        fragments.append(f'<circle cx="{zx+50}" cy="{zy+50}" r="4" fill="none" stroke="#b52e50"/><text x="{zx}" y="{zy+115}" class="small">camera zoom</text>')
        witnessed=sum(c['witness_count']>0 for c in result['components'])
        fragments.append(f'<text x="{ox}" y="{oy+433}" class="note">{witnessed} witnessed / {len(result["components"])} outer components; n=256</text>')
    fragments.extend(['<rect x="28" y="1035" width="14" height="14" fill="#eab66b"/><text x="50" y="1047" class="note">outer boundary cells</text>',
                      '<rect x="270" y="1035" width="14" height="14" fill="#23806d"/><text x="292" y="1047" class="note">inner cells</text>',
                      '<circle cx="440" cy="1042" r="5" fill="none" stroke="#b52e50" stroke-width="2"/><text x="455" y="1047" class="note">synthetic source camera</text>',
                      '<text x="28" y="1073" class="note">Adding o3 removes the reflected branch; the unlabeled singular cover near B has no center witness.</text>',
                      '<text x="28" y="1096" class="small">Assistant-generated synthetic geometry and labels. No human review. Outer cover clusters do not certify exact solutions.</text></svg>'])
    path.write_text('\n'.join(fragments)+'\n')


def evaluate(data=ROOT/'data',output=ROOT/'reports',n=128,reference_n=256):
    start=time.perf_counter();pairs=[]
    for path in sorted((data/'inputs').glob('*.json')):
        scene=json.loads(path.read_text());truth=json.loads((data/'truth'/path.name).read_text());pairs.append((scene,truth))
    rows=[audit_scene(s,t,n,reference_n) for s,t in pairs]
    by_split=defaultdict(list)
    for row in rows: by_split[row['split']].append(row)
    summary={split:{'count':len(items),'truth_exact_accepted':sum(r['truth_exact_accepted'] for r in items),
                    'truth_outer_covered':sum(r['truth_outer_covered'] for r in items),
                    'valid_truth_count':sum(r['truth_exact_accepted'] for r in items),
                    'valid_truth_outer_covered':sum(r['truth_exact_accepted'] and r['truth_outer_covered'] for r in items),
                    'discretization_center_misses':sum(r['discretization_center_miss'] for r in items)}
             for split,items in sorted(by_split.items())}
    valid_bounded=[(s,t) for s,t in pairs if s['noise_model']['kind']=='bounded' and accepts(s,t['camera'],s['default_observations'])]
    monotone=[monotonicity(s,n) for s,t in valid_bounded]
    nested=[nesting(s) for s,t in pairs if s['split']=='analytic' or s['id'] in [f'benchmark-{i:02}' for i in range(1,5)]]
    supplemental=[audit_scene(s,t,256,256) for s,t in pairs if s['id'] in [f'benchmark-{i:02}' for i in range(1,5)]]
    report={'schema_version':1,'python':platform.python_version(),'seed':240017,'scene_count':len(rows),
            'resolution':n,'reference_resolution':reference_n,'split_summary':summary,'scenes':rows,
            'monotonicity':monotone,'resolution_nesting':nested,'teaching_at_256':supplemental,
            'failures':failure_counts(rows, supplemental, monotone, nested),
            'classification_counts':dict(Counter(r['classification'] for r in rows)),
            'total_runtime_seconds':time.perf_counter()-start,
            'limitations':['Numerical real-arithmetic enclosure argument; no formal floating-point guarantee.',
                           'Dense sampled areas and empty samples do not prove continuous feasibility or conflict.',
                           'Unwitnessed outer components may be conservative artifacts or real regions missed by centers.',
                           'Synthetic assistant-generated annotations; no human review or novelty claim.']}
    output.mkdir(parents=True,exist_ok=True)
    (output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    teaching=[(s,t) for s,t in pairs if s['id'] in [f'benchmark-{i:02}' for i in range(1,5)]]
    teaching_svg(teaching,output/'teaching.svg')
    lines=['# Numerical coverage audit','',f'Executed with Python {platform.python_version()}, seed 240017. All {len(rows)} scenes use solver n={n} and independent dense reference n={reference_n}. Total audit runtime: {report["total_runtime_seconds"]:.2f} seconds.','',
           '| Split | Scenes | Exact truth accepted | Truth in outer cover | Valid truth covered / valid truth | Center misses for valid truth |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    for split,x in summary.items():
        lines.append(f'| {split} | {x["count"]} | {x["truth_exact_accepted"]} | {x["truth_outer_covered"]} | {x["valid_truth_outer_covered"]}/{x["valid_truth_count"]} | {x["discretization_center_misses"]} |')
    lines+=['',f'Independent reference points excluded by the outer cover: {report["failures"]["reference_points_missed"]}. Inner-cell corner and center failures: {report["failures"]["inner_point_failures"]} across {sum(r["inner_point_checks"] for r in rows)} checks.',
            '', f'The n=128 audit has {sum(r["inner_point_checks"] for r in rows)} inner-cell point checks because no inner cells survive at that resolution. A supplementary n=256 audit of the four teaching scenes checks {sum(r["inner_point_checks"] for r in supplemental)} inner-cell corner/center points, with {sum(r["inner_point_failures"] for r in supplemental)} failures. At n=256 the teaching cases have outer/witnessed component counts ' + ', '.join(f'{r["outer_components"]}/{r["witnessed_components"]}' for r in supplemental) + '. The extra unwitnessed component in each ambiguous case needs no interpretation as a true solution.',
            '',f'Every observation prefix was compared for {len(monotone)} valid bounded scenes at n={n}: {sum(r["prefix_comparisons"] for r in monotone)} comparisons, {report["failures"]["nonmonotone_added_cells"]} added cells. Analytic and four teaching scenes were checked at n=64,128,256: {report["failures"]["non_nested_cells"]} non-nested cells.',
            '',f'Area bracket widths range from {min(r["area_bracket_width"] for r in rows):.6g} to {max(r["area_bracket_width"] for r in rows):.6g} square metres. The sampled reference area falls inside the computed bracket in {sum(r["reference_area_within_bracket"] for r in rows)}/{len(rows)} scenes. Full per-scene areas and runtimes are in evaluation.json.',
            '',f'Summed solver runtime: {sum(r["solver_runtime_ms"] for r in rows):.2f} ms. Summed dense reference runtime: {sum(r["reference_runtime_ms"] for r in rows):.2f} ms. These are one-run timings on this host.',
            '', 'Analytic fixtures check the triangle intersection [1,2], reflected solutions [1,3] and [1,-3], and the deliberately contradictory same-landmark bearings. Exact zero-area sets can lack cell-center witnesses. The analytic reflection fixture retains three outer components at n=128 and no center witnesses: two cover the known reflected points and the third lies near a landmark singularity. This extra outer cluster does not establish a third exact solution.',
            '', 'Teaching scenes use unsigned angles to collinear A, B, C. Reflection across y=0 preserves both angles; adding calibrated bearing o3 selects the positive-y branch. The SVG shows two ambiguous defaults and two resolved defaults. Outer cover components and independently meaningful center witnesses are counted separately in evaluation.json; an unwitnessed component does not establish another solution.',
            '', 'The Gaussian extension uses one-sigma intervals, so its exact truth acceptance is empirical. Model violations and deliberately corrupted correspondences are recorded separately from numerical truth exclusion. An exact valid truth point can lie in the outer cover while its cell center fails the constraints; the center-miss column measures that discretization effect.',
            '', 'The enclosure argument assumes real arithmetic. The floating-point implementation uses an empirical angular pad and has no formal floating-point guarantee. Dense sampling supplies numerical evidence; it cannot certify the absence of a continuous solution. An outer component without a witness may be a conservative artifact or a small real region. All scenes and teaching annotations were generated by the assistant without human review. No novelty claim is made.',
            '', 'Reproduce with `python3 -m geolab.evaluate` and `python3 -m unittest discover -s tests -v`.']
    (output/'coverage.md').write_text('\n'.join(lines)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=ROOT/'data');parser.add_argument('--output',type=Path,default=ROOT/'reports')
    args=parser.parse_args();report=evaluate(args.data,args.output)
    print(json.dumps({k:report[k] for k in ['scene_count','split_summary','failures','classification_counts','total_runtime_seconds']},indent=2))
    if any(report['failures'].values()):
        raise SystemExit(1)

if __name__=='__main__':main()
