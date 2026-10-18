"""Assistant-authored adversarial checks with analytic geometry and independent predicates."""
import math
import unittest
from geolab.solver import solve, contains


def scene(bounds, landmarks, observations):
    return {'id':'adversarial','bounds':bounds,'landmarks':[
        {'id':key,'x':point[0],'y':point[1]} for key, point in landmarks.items()],
        'observations':observations}


def obs(key, kind, names, value, tolerance=0):
    return {'id':key,'kind':kind,'landmarks':names,'value_deg':value,'tolerance_deg':tolerance}


def independent_accepts(s, p):
    lm = {v['id']:(v['x'], v['y']) for v in s['landmarks']}
    for o in s['observations']:
        rays = [(lm[k][0]-p[0], lm[k][1]-p[1]) for k in o['landmarks']]
        if any(x == y == 0 for x,y in rays):
            return False
        if o['kind'] == 'angle':
            a,b = rays
            val = math.degrees(math.atan2(abs(a[0]*b[1]-a[1]*b[0]), a[0]*b[0]+a[1]*b[1]))
            err = abs(val-o['value_deg'])
        else:
            v = complex(*rays[0])/complex(math.cos(math.radians(o['value_deg'])),math.sin(math.radians(o['value_deg'])))
            err = abs(math.degrees(math.atan2(v.imag,v.real)))
        if err > o['tolerance_deg']+1e-10:
            return False
    return True


class AdversarialGeometryTests(unittest.TestCase):
    def test_right_angle_circle(self):
        # Thales: the entire unit circle except the two landmarks is feasible.
        s=scene([-2,-2,2,2], {'A':(-1,0),'B':(1,0)}, [obs('a','angle',['A','B'],90)])
        for n in (8,32,128):
            r=solve(s,n)
            for i in range(1,72):
                t=2*math.pi*i/72
                if i==36: continue
                p=(math.cos(t), math.sin(t))
                self.assertTrue(independent_accepts(s,p))
                self.assertTrue(contains(r,p),(n,p))
            self.assertEqual(r['area_lower'],0)

    def test_reflected_exact_pair_and_resolving_bearing(self):
        s=scene([-2,-2,2,2], {'A':(-1,0),'B':(0,0),'D':(1,0)},
                [obs('a','angle',['A','B'],45),obs('b','angle',['B','D'],45)])
        r=solve(s,128)
        self.assertTrue(contains(r,(0,1)))
        self.assertTrue(contains(r,(0,-1)))
        self.assertGreaterEqual(len(r['components']),2)
        # A conservative unresolved cluster can persist at the singular landmark.
        labels={(x,y):label for x,y,_,label in r['cells']}
        self.assertNotEqual(labels[(64,96)],labels[(64,32)])
        s['observations'].append(obs('c','bearing',['A'],225))
        r=solve(s,128)
        self.assertTrue(contains(r,(0,1)))
        self.assertFalse(contains(r,(0,-1)))

    def test_rectangular_cover_and_inner_corners(self):
        s=scene([-100,-.05,100,.05], {'A':(5,0),'B':(-4,.02)},
                [obs('a','bearing',['A'],0,12),obs('b','angle',['A','B'],180,15)])
        r=solve(s,64)
        for i in range(129):
            for j in range(17):
                p=(-100+i*200/128,-.05+j*.1/16)
                if independent_accepts(s,p): self.assertTrue(contains(r,p),p)
        for x,y,k,_ in r['cells']:
            if k:
                for ox,oy in ((0,0),(0,1),(1,0),(1,1),(.5,.5)):
                    self.assertTrue(independent_accepts(s,(-100+(x+ox)*200/64,-.05+(y+oy)*.1/64)))

    def test_subdivision_and_added_constraint_outer_monotonicity(self):
        s=scene([-3,-2,3,2], {'A':(-1,0),'B':(1,0)},
                [obs('a','angle',['A','B'],90,5),obs('b','bearing',['A'],225,8)])
        for selected in (['a'],['a','b']):
            prev=None
            for n in (8,16,32,64):
                r=solve(s,n,selected)
                cells={(c[0],c[1]) for c in r['cells']}
                if prev is not None:
                    self.assertTrue(all((x//2,y//2) in prev for x,y in cells))
                prev=cells
            base=solve(s,64,['a'])
            self.assertLessEqual(cells,{(c[0],c[1]) for c in base['cells']})

    def test_circular_conflict_threshold_and_reversed_angle_order(self):
        s=scene([-2,-2,2,2], {'A':(-1,0),'B':(1,0)},
                [obs('a','bearing',['A'],359,1),obs('b','bearing',['A'],1,1)])
        r=solve(s,64)
        self.assertFalse(r['conflict_observations'])
        self.assertTrue(contains(r,(-2,0)))
        s['observations'][1]['value_deg']=2
        self.assertEqual(solve(s,64)['status'],'incompatible')
        s['observations']=[obs('a','angle',['A','B'],45,1),obs('b','angle',['B','A'],50,1)]
        self.assertEqual(solve(s,64)['status'],'incompatible')

    def test_used_landmark_singularity_never_inner(self):
        s=scene([-1,-1,1,1], {'A':(0,0)},[obs('a','bearing',['A'],0,180)])
        r=solve(s,8)
        # Four closed cells meet at the singular landmark.
        for x,y,k,_ in r['cells']:
            if x in (3,4) and y in (3,4): self.assertEqual(k,0)

if __name__=='__main__': unittest.main()
