"""Hand-derived examples for the event-driven dispatch policies."""

from copy import deepcopy
import unittest

from dispatch.simulate import simulate


def fixture():
    """Four requests; the sole charger forces two useful serial charges."""
    return {
        "id": "hand-simulator", "seed": 0, "horizon": 8, "slot_minutes": 1,
        "load_time": 1, "handoff_time": 0, "turnaround_time": 0,
        "charge_duration": 2,
        "vehicles": [{"id": "V1", "unavailable": []},
                     {"id": "V2", "unavailable": []}],
        "battery_ids": ["B1", "B2"], "charger_ids": ["C1"],
        "technician_ids": ["T1", "T2"],
        "travel": {"Depot": {"Depot": 0, "North": 1},
                   "North": {"Depot": 0, "North": 0}},
        "requests": [
            {"id": f"R{i}", "release": 0, "deadline": deadline,
             "region": "North", "category": "generic", "priority": 1,
             "cancelled": False}
            for i, deadline in enumerate([2, 2, 6, 8], 1)
        ],
        "weights": {"rejection": 200, "lateness": 1, "charge": 1,
                    "fairness": 0},
    }


class SimulatorTests(unittest.TestCase):
    def test_hand_case_charger_conflict_and_return_boundary(self):
        s = fixture()
        schedule = simulate(s)
        self.assertEqual(
            [(r["request_id"], r["start"], r["delivery"], r["end"])
             for r in schedule["services"]],
            [("R1", 0, 2, 2), ("R2", 0, 2, 2),
             ("R3", 4, 6, 6), ("R4", 6, 8, 8)],
        )
        self.assertEqual(
            [(c["battery_id"], c["start"], c["end"])
             for c in schedule["charges"]],
            [("B1", 2, 4), ("B2", 4, 6), ("B1", 6, 8)],
        )
        self.assertEqual(schedule["unserved"], [])

    def test_loading_completion_wakes_dispatch_before_vehicle_return(self):
        s = fixture()
        s["technician_ids"] = ["T1"]
        s["travel"]["Depot"]["North"] = 3
        s["requests"] = s["requests"][:2]
        schedule = simulate(s)
        self.assertEqual([r["start"] for r in schedule["services"]], [0, 1])

    def test_fcfs_and_edf_have_distinct_pending_order(self):
        s = fixture()
        s["vehicles"] = s["vehicles"][:1]
        s["requests"] = s["requests"][:2]
        s["requests"][0]["deadline"] = 8
        fcfs = simulate(s, "fcfs")
        edf = simulate(s, "edf")
        self.assertEqual([r["request_id"] for r in fcfs["services"]], ["R1", "R2"])
        self.assertEqual([r["request_id"] for r in edf["services"]], ["R2", "R1"])

    def test_long_head_request_is_bypassed_and_calendar_end_wakes_it(self):
        s = fixture()
        s["horizon"] = 10
        s["vehicles"] = [{"id": "V1", "unavailable": [[2, 4]]}]
        s["requests"] = s["requests"][:2]
        s["requests"][0]["region"] = "Far"
        s["travel"] = {
            "Depot": {"Depot": 0, "North": 1, "Far": 2},
            "North": {"Depot": 0, "North": 0, "Far": 0},
            "Far": {"Depot": 0, "North": 0, "Far": 0},
        }
        schedule = simulate(s)
        self.assertEqual([(r["request_id"], r["start"], r["end"])
                          for r in schedule["services"]],
                         [("R2", 0, 2), ("R1", 4, 7)])

    def test_no_vehicle_gives_explanatory_rejections(self):
        s = fixture()
        s["vehicles"] = []
        schedule = simulate(s)
        self.assertEqual(schedule["services"], [])
        self.assertEqual(len(schedule["unserved"]), 4)
        self.assertTrue(all(r["status"] == "rejected" and "vehicle" in r["reason"]
                            for r in schedule["unserved"]))

    def test_calendar_prevents_every_complete_service(self):
        s = fixture()
        s["vehicles"] = [{"id": "V1", "unavailable": [[0, 7]]}]
        schedule = simulate(s)
        self.assertEqual(schedule["services"], [])
        self.assertTrue(all("availability" in r["reason"] for r in schedule["unserved"]))

    def test_cancelled_arrival_never_acquires_resources(self):
        s = fixture()
        s["requests"] = s["requests"][:2]
        s["requests"][0].update(cancelled=True, release=4)
        schedule = simulate(s, information="online")
        self.assertEqual([r["request_id"] for r in schedule["services"]], ["R2"])
        self.assertEqual(schedule["unserved"][0]["status"], "cancelled")
        for decision in schedule["decisions"]:
            if decision["time"] < 4:
                self.assertNotIn("R1", decision["visible_request_ids"])

    def test_complete_return_must_fit_horizon(self):
        s = fixture()
        s["horizon"] = 2
        s["travel"]["North"]["Depot"] = 1
        schedule = simulate(s)
        self.assertEqual(schedule["services"], [])
        self.assertTrue(all("horizon" in r["reason"] for r in schedule["unserved"]))

    def test_empty_demand_has_no_operations(self):
        s = fixture()
        s["requests"] = []
        schedule = simulate(s)
        self.assertEqual(schedule["services"], [])
        self.assertEqual(schedule["charges"], [])
        self.assertEqual(schedule["unserved"], [])

    def test_battery_cannot_charge_while_mission_is_in_progress(self):
        s = fixture()
        s["horizon"] = 10
        s["battery_ids"] = ["B1"]
        s["travel"]["Depot"]["North"] = 2
        s["requests"] = s["requests"][:2]
        s["requests"][1]["release"] = 1
        schedule = simulate(s)
        self.assertEqual([(r["start"], r["end"]) for r in schedule["services"]],
                         [(0, 3), (5, 8)])
        self.assertEqual([(r["start"], r["end"]) for r in schedule["charges"]],
                         [(3, 5), (8, 10)])

    def test_online_prefix_is_unchanged_by_arbitrary_future_requests(self):
        s = fixture()
        s["horizon"] = 14
        s["requests"] = s["requests"][:2]
        future = deepcopy(s)
        extra = deepcopy(s["requests"][0])
        extra.update(id="FUTURE", release=7, deadline=0, priority=1000,
                     cancelled=True)
        future["requests"].append(extra)
        for cancelled in [False, True]:
            future["requests"][-1]["cancelled"] = cancelled
            for policy in ["fcfs", "edf"]:
                base = simulate(s, policy, "online")
                changed = simulate(future, policy, "online")
                for field in ["services", "charges"]:
                    self.assertEqual([x for x in base[field] if x["start"] < 7],
                                     [x for x in changed[field] if x["start"] < 7])
                self.assertEqual([x for x in base["decisions"] if x["time"] < 7],
                                 [x for x in changed["decisions"] if x["time"] < 7])

    def test_missing_loading_or_energy_resources_are_explicit(self):
        for field, reason in [("technician_ids", "technician"),
                              ("battery_ids", "battery")]:
            s = fixture()
            s[field] = []
            schedule = simulate(s)
            self.assertEqual(schedule["services"], [])
            self.assertEqual(len(schedule["unserved"]), 4)
            self.assertTrue(all(reason in r["reason"] for r in schedule["unserved"]))

    def test_no_charger_exhausts_only_the_initial_batteries(self):
        s = fixture()
        s["charger_ids"] = []
        schedule = simulate(s)
        self.assertEqual(len(schedule["services"]), 2)
        self.assertEqual(schedule["charges"], [])
        self.assertEqual(len(schedule["unserved"]), 2)
        self.assertTrue(all("charger" in r["reason"] for r in schedule["unserved"]))

    def test_after_horizon_release_has_record_without_early_visibility(self):
        s = fixture()
        s["requests"] = s["requests"][:1]
        s["requests"][0]["release"] = 9
        schedule = simulate(s, information="online")
        self.assertEqual(len(schedule["unserved"]), 1)
        self.assertIn("horizon", schedule["unserved"][0]["reason"])
        self.assertTrue(all(d["visible_request_ids"] == [] for d in schedule["decisions"]))

    def test_seeded_benchmarks_pass_independent_checker_in_both_modes(self):
        from dispatch.checker import validate_schedule
        from dispatch.generate import benchmark, sensitivity_cases

        for name, s in sensitivity_cases(benchmark()):
            for information in ["offline", "online"]:
                for policy in ["fcfs", "edf"]:
                    with self.subTest(case=name, policy=policy, information=information):
                        self.assertEqual(validate_schedule(s, simulate(s, policy, information)), [])

    def test_resources_and_simultaneous_requests_use_id_ties(self):
        s = fixture()
        s["vehicles"].reverse()
        s["battery_ids"].reverse()
        s["technician_ids"].reverse()
        s["requests"].reverse()
        first = simulate(s)["services"][0]
        self.assertEqual((first["request_id"], first["vehicle_id"],
                          first["battery_id"], first["technician_id"]),
                         ("R1", "V1", "B1", "T1"))

    def test_input_is_not_mutated_and_bad_modes_are_rejected(self):
        s = fixture()
        original = deepcopy(s)
        simulate(s)
        self.assertEqual(s, original)
        with self.assertRaises(ValueError):
            simulate(s, "unknown")
        with self.assertRaises(ValueError):
            simulate(s, information="clairvoyant")


if __name__ == "__main__":
    unittest.main()
