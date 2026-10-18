import copy
import math
import unittest

from geolab.solver import solve, contains, point_feasible


def triangle(tol=0.0):
    return {"id": "test", "bounds": [-5, -5, 5, 5],
            "landmarks": [{"id": "A", "x": 3, "y": 0}, {"id": "B", "x": 0, "y": 4}],
            "observations": [
                {"id": "a", "kind": "bearing", "landmarks": ["A"], "value_deg": 0, "tolerance_deg": tol},
                {"id": "b", "kind": "bearing", "landmarks": ["B"], "value_deg": 90, "tolerance_deg": tol}]}


class SolverTests(unittest.TestCase):
    def test_zero_width_triangle_preserved(self):
        result = solve(triangle(), 64)
        self.assertTrue(contains(result, [0, 0]))
        self.assertGreater(len(result["cells"]), 0)
        self.assertEqual(result["area_lower"], 0)
        self.assertEqual(result["status"], "unresolved")

    def test_narrow_off_grid_truth(self):
        scene = triangle(0.0001)
        truth = [0.017, 0.031]
        for obs, lm in zip(scene["observations"], scene["landmarks"]):
            obs["value_deg"] = math.degrees(math.atan2(lm["y"] - truth[1], lm["x"] - truth[0]))
        self.assertTrue(contains(solve(scene, 32), truth))

    def test_constraint_monotonicity(self):
        scene = triangle(4)
        before = solve(scene, 64, ["a"])
        after = solve(scene, 64)
        a = {(c[0], c[1]) for c in before["cells"]}
        b = {(c[0], c[1]) for c in after["cells"]}
        self.assertLessEqual(b, a)

    def test_conflicting_bearings_even_at_landmark(self):
        scene = triangle(1)
        scene["observations"][1] = dict(scene["observations"][0], id="b", value_deg=180)
        result = solve(scene, 32)
        self.assertEqual(result["status"], "incompatible")
        self.assertEqual(result["cells"], [])
        self.assertEqual(result["conflict_observations"], ["a", "b"])

    def test_wraparound(self):
        scene = triangle(2)
        scene["observations"] = [dict(scene["observations"][0], value_deg=359)]
        self.assertTrue(point_feasible(scene, [0, 0]))
        self.assertTrue(contains(solve(scene, 32), [0, 0]))

    def test_singular_landmark_is_not_witness(self):
        self.assertFalse(point_feasible(triangle(180), [3, 0]))

    def test_no_constraints_returns_domain(self):
        result = solve(triangle(), 8, [])
        self.assertEqual(result["area_lower"], 100)
        self.assertEqual(result["area_upper"], 100)
        self.assertTrue(contains(result, [5, 5]))

    def test_invalid_inputs(self):
        for bad in [0, 33, 1024, True]:
            with self.assertRaises(ValueError):
                solve(triangle(), bad)
        with self.assertRaises(ValueError):
            solve(triangle(), 32, ["missing"])
        bad = copy.deepcopy(triangle())
        bad["observations"][0]["value_deg"] = float("nan")
        with self.assertRaises(ValueError):
            solve(bad, 32)

    def test_inner_cells_obey_all_constraints_at_corners(self):
        scene = triangle(8)
        result = solve(scene, 64)
        self.assertGreater(result["area_lower"], 0)
        for ix, iy, kind, _ in result["cells"]:
            if kind == 1:
                for ox, oy in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                    p = [-5 + (ix + ox) * 10 / 64, -5 + (iy + oy) * 10 / 64]
                    self.assertTrue(point_feasible(scene, p), p)


if __name__ == "__main__":
    unittest.main()
