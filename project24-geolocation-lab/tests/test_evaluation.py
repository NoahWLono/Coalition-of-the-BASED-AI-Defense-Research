import unittest
from geolab.evaluate import audit_scene, monotonicity, nesting, failure_counts
from geolab.generate import analytic_fixtures, generate_all


class EvaluationTests(unittest.TestCase):
    def test_supplemental_truth_and_reference_exclusions_fail_gate(self):
        row = {'reference_points_missed': 0, 'truth_exact_accepted': True,
               'truth_outer_covered': False, 'inner_point_failures': 0}
        supplemental = dict(row, reference_points_missed=2)
        failures = failure_counts([row], [supplemental], [], [])
        self.assertEqual(failures['valid_truth_exclusions'], 2)
        self.assertEqual(failures['reference_points_missed'], 2)
        self.assertTrue(any(failures.values()))

    def test_exact_triangle_coverage_and_center_discretization(self):
        scene,truth=analytic_fixtures()[0]
        row=audit_scene(scene,truth,32,64)
        self.assertTrue(row['truth_exact_accepted'])
        self.assertTrue(row['truth_outer_covered'])
        self.assertTrue(row['discretization_center_miss'])
        self.assertEqual(row['reference_points_missed'],0)

    def test_inner_corner_checks_are_nonvacuous(self):
        scene,truth=analytic_fixtures()[0]
        for observation in scene['observations']:
            observation['tolerance_deg']=20
        row=audit_scene(scene,truth,32,64)
        self.assertGreater(row['inner_point_checks'],0)
        self.assertEqual(row['inner_point_failures'],0)

    def test_conflict_classified(self):
        scene,truth=analytic_fixtures()[2]
        row=audit_scene(scene,truth,32,64)
        self.assertEqual(row['classification'],'inconsistent evidence')
        self.assertEqual(row['area_upper'],0)

    def test_monotonicity_and_nesting(self):
        scene,_=generate_all()[5]
        self.assertEqual(monotonicity(scene,32)['added_cells'],0)
        self.assertEqual(nesting(scene)['non_nested_cells'],0)

if __name__=='__main__':unittest.main()
