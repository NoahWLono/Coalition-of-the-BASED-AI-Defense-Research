import json
import tempfile
from pathlib import Path
import unittest
from geolab.generate import analytic_fixtures, generate_all, write_pairs
from geolab.reference import accepts, dense_grid


class ReferenceTests(unittest.TestCase):
    def test_triangle(self):
        scene, truth = analytic_fixtures()[0]
        self.assertTrue(accepts(scene, truth['camera']))
        self.assertFalse(accepts(scene, [2,2]))
        self.assertFalse(accepts(scene, [0,0]))

    def test_reflections(self):
        scene, truth = analytic_fixtures()[1]
        for point in truth['exact_solutions']:
            self.assertTrue(accepts(scene, point))
        for point in ([1,2],[-1,3],[0,0],[-4,0],[4,0]):
            self.assertFalse(accepts(scene, point))

    def test_conflict(self):
        scene, _ = analytic_fixtures()[2]
        self.assertEqual(dense_grid(scene,32)['accepted_count'],0)

    def test_generated_wrap_interval(self):
        scene,truth=next((s,t) for s,t in generate_all() if s['id']=='benchmark-05')
        exact=truth['observations'][1]['exact_value_deg']
        self.assertGreater(exact,358.5)
        self.assertGreater(exact+scene['observations'][1]['tolerance_deg'],360)

    def test_grid_area_and_validation(self):
        scene,_=analytic_fixtures()[0]
        result=dense_grid(scene,8,[])
        self.assertEqual(result['accepted_count'],64)
        self.assertEqual(result['area'],224)
        with self.assertRaises(ValueError): dense_grid(scene,0)

    def test_wraparound(self):
        scene,_=analytic_fixtures()[0]
        scene['observations']=[dict(scene['observations'][0], value_deg=359,tolerance_deg=2)]
        scene['default_observations']=['o1']
        self.assertTrue(accepts(scene,[-1,0]))

    def test_analytic_generation_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest=write_pairs(analytic_fixtures(),Path(folder))
            self.assertEqual(manifest['split_counts'],{'analytic':3})
            value=json.loads((Path(folder)/'inputs/analytic-triangle.json').read_text())
            self.assertNotIn('camera',value)

    def test_splits_determinism_and_truth(self):
        pairs=generate_all()
        self.assertEqual(pairs,generate_all())
        counts={split:sum(s['split']==split for s,t in pairs) for split in {s['split'] for s,t in pairs}}
        self.assertEqual(counts,{'analytic':3,'benchmark':20,'tuning':4,'heldout-bounded':12,'heldout-gaussian':12})
        for scene,truth in pairs:
            self.assertNotIn('camera',scene)
            if scene['split'] in ('tuning','heldout-bounded'):
                self.assertTrue(accepts(scene,truth['camera']),scene['id'])

    def test_teaching_grid_reflections_and_added_constraint(self):
        for scene,truth in generate_all()[3:7]:
            base=dense_grid(scene,128,['o1','o2'])
            resolved=dense_grid(scene,128,['o1','o2','o3'])
            self.assertTrue(any(p[1]>0 for p in base['points']))
            self.assertTrue(any(p[1]<0 for p in base['points']))
            self.assertTrue(resolved['points'])
            self.assertTrue(all(p[1]>0 for p in resolved['points']))
            self.assertLess(resolved['area'],base['area'])

if __name__=='__main__': unittest.main()
