"""Deterministic synthetic data and separately stored answer keys."""
import argparse
import json
import math
from pathlib import Path
import random

SEED = 240017


def observations(landmarks, camera, specs, rng=None, model='exact', tolerance=0):
    # Truth path uses normalized dot products and acos for angles, unlike reference.
    lookup = {p['id']: (p['x'], p['y']) for p in landmarks}
    result, errors = [], []
    for index, (kind, ids) in enumerate(specs):
        vectors = [(lookup[k][0]-camera[0], lookup[k][1]-camera[1]) for k in ids]
        if kind == 'bearing':
            exact = math.degrees(math.atan2(vectors[0][1], vectors[0][0])) % 360
        else:
            a, b = vectors
            cosine = sum(u*v for u,v in zip(a,b))/(math.hypot(*a)*math.hypot(*b))
            exact = math.degrees(math.acos(max(-1, min(1, cosine))))
        error = (rng.uniform(-tolerance, tolerance) if model == 'bounded' else
                 rng.gauss(0, tolerance) if model == 'gaussian' else 0)
        value = exact + error
        if kind == 'bearing':
            value %= 360
        else:
            value = max(0, min(180, value))
        result.append({'id': f'o{index+1}', 'kind': kind, 'landmarks': ids,
                       'value_deg': value, 'tolerance_deg': tolerance,
                       'label': f'{kind} to {", ".join(ids)}'})
        errors.append({'observation_id': f'o{index+1}', 'exact_value_deg': exact,
                       'drawn_error_deg': error, 'reported_value_deg': value})
    return result, errors


def make_scene(identifier, title, split, landmarks, camera, specs, tolerance=1.0,
               model='bounded', rng=None, defaults=None, bounds=(-8,-7,8,7)):
    obs, errors = observations(landmarks, camera, specs, rng or random.Random(SEED), model, tolerance)
    scene = {'id': identifier, 'title': title, 'split': split,
             'description': 'Fictional local geometry; assistant-generated teaching labels.',
             'bounds': list(bounds), 'landmarks': landmarks, 'observations': obs,
             'default_observations': defaults or [o['id'] for o in obs],
             'noise_model': {'kind': model, 'angular_units': 'degrees', 'tolerance_deg': tolerance,
                             'interval_sigma_multiplier': 1 if model == 'gaussian' else None,
                             'seed': SEED, 'coordinates': 'arbitrary local metres'},
             'teaching': {'annotation_producer': 'assistant', 'human_review': False}}
    truth = {'scene_id': identifier, 'camera': camera, 'observations': errors,
             'annotation_producer': 'assistant', 'human_review': False}
    return scene, truth


def analytic_fixtures():
    landmarks = [{'id':'A','x':0,'y':0,'label':'A'}, {'id':'B','x':4,'y':0,'label':'B'}]
    triangle = make_scene('analytic-triangle','Two calibrated bearings intersect','analytic',landmarks,[1,2],
                          [('bearing',['A']),('bearing',['B'])],0,'exact')
    collinear = [{'id':k,'x':x,'y':0,'label':k} for k,x in [('A',-4),('B',0),('C',4)]]
    reflected = make_scene('analytic-reflection','Two unsigned angles admit reflected points','analytic',collinear,[1,3],
                           [('angle',['A','B']),('angle',['B','C'])],0,'exact')
    reflected[1]['exact_solutions'] = [[1,3],[1,-3]]
    conflict = make_scene('analytic-conflict','Incompatible bearings to one landmark','analytic',landmarks,[1,2],
                         [('bearing',['A']),('bearing',['A'])],0,'exact')
    conflict[0]['observations'][0]['value_deg'] = 0
    conflict[0]['observations'][1]['value_deg'] = 90
    conflict[0]['teaching']['explanation'] = 'Two different zero-tolerance bearings to the same landmark cannot hold at one camera. The measurements were deliberately corrupted; removing either one restores a ray of possibilities.'
    conflict[1]['expected_feasible'] = False
    conflict[1]['annotations'] = 'Deliberately corrupted observations; camera is source geometry only.'
    return [triangle, reflected, conflict]


def generate_all():
    pairs = analytic_fixtures()
    rng = random.Random(SEED)
    collinear = [{'id':k,'x':x,'y':0,'label':k} for k,x in [('A',-4),('B',0),('C',4)]]
    for i in range(4):
        specs = [('angle',['A','B']),('angle',['B','C']),('bearing',['A'])]
        s,t = make_scene(f'benchmark-{i+1:02}', ['Reflection ambiguity I','Reflection ambiguity II','Reflection resolved I','Reflection resolved II'][i],
                         'benchmark',collinear,[1 if i%2==0 else -1,3],specs,1.8,'exact',
                         defaults=['o1','o2'] if i<2 else ['o1','o2','o3'])
        s['teaching'].update({'base_observations':['o1','o2'],'additional_observation':'o3',
                              'explanation':'Angles preserve reflection across y=0; calibrated bearing selects a side.'})
        t['reflected_camera'] = [t['camera'][0],-3]
        pairs.append((s,t))
    for split, count, model in [('benchmark',16,'bounded'),('tuning',4,'bounded'),('heldout-bounded',12,'bounded'),('heldout-gaussian',12,'gaussian')]:
        for j in range(count):
            index = j+5 if split == 'benchmark' else j+1
            landmarks = [{'id':chr(65+k),'x':x,'y':y,'label':chr(65+k)} for k,(x,y) in enumerate([(-5,-2),(4,-1),(0,5),(5,4)])]
            camera = [rng.uniform(-2.5,2.5),rng.uniform(-1,2.5)]
            specs = [('bearing',['A']),('bearing',['B']),('angle',['B','C'])]
            title = 'Gaussian synthetic observations' if model == 'gaussian' else 'Bounded synthetic observations'
            if split=='benchmark' and j==0:
                camera=[-2,-0.95]; title='Bearing wraparound near 360 degrees'
            if split=='benchmark' and j in (1,2):
                landmarks=[{'id':chr(65+k),'x':x,'y':y,'label':chr(65+k)} for k,(x,y) in enumerate([(-4,0),(0,0),(4,0),(8,0)])]
                title='Collinear repeated layout'
            s,t = make_scene(f'{split}-{index:02}',title,split,landmarks,camera,specs,1.5,model,rng)
            if split=='benchmark' and j==3:
                s['observations'][0]['landmarks']=['D']; s['title']='Incorrect landmark correspondence'
                t['annotations']='Observation o1 was generated for A and assigned to D.'
                s['teaching']['explanation']='Observation o1 was deliberately assigned to the wrong landmark. Incompatibility can expose a mistake, but a surviving region would not prove the identity correct. Toggle o1 to see its effect, then reveal the source camera.'
            if split=='benchmark' and j==4:
                s['observations'].append(dict(s['observations'][0],id='o4',value_deg=(s['observations'][0]['value_deg']+90)%360))
                s['default_observations'].append('o4'); s['title']='Contradictory repeated bearing'
                t['expected_feasible']=False
                s['teaching']['explanation']='The repeated bearing o4 deliberately contradicts o1. Their intervals do not overlap. Remove either measurement to inspect the remaining evidence.'
            pairs.append((s,t))
    return pairs


def write_pairs(pairs, root):
    for section in ('inputs','truth'):
        (root/section).mkdir(parents=True,exist_ok=True)
    for scene, truth in pairs:
        for section, value in [('inputs',scene),('truth',truth)]:
            (root/section/f'{scene["id"]}.json').write_text(json.dumps(value,indent=2)+'\n')
    manifest={'seed':SEED,'scene_ids':[s['id'] for s,t in pairs],
              'split_counts':{split:sum(s['split']==split for s,t in pairs) for split in sorted({s['split'] for s,t in pairs})},
              'annotation_producer':'assistant','human_review':False}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data')
    parser.add_argument('--analytic-only',action='store_true')
    args=parser.parse_args()
    print(json.dumps(write_pairs(analytic_fixtures() if args.analytic_only else generate_all(),args.output),indent=2))

if __name__=='__main__': main()
