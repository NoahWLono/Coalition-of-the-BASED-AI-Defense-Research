"""Hand-derived tests for the independent tiny-instance enumeration."""

from copy import deepcopy

import pytest


def scenario(requests=None):
    return {
        "id": "reference-hand", "seed": 0, "horizon": 8, "slot_minutes": 1,
        "load_time": 1, "handoff_time": 0, "turnaround_time": 0,
        "charge_duration": 2,
        "vehicles": [{"id": "V1", "unavailable": []}, {"id": "V2", "unavailable": []}],
        "battery_ids": ["B1", "B2"], "charger_ids": ["C1"],
        "technician_ids": ["T1", "T2"],
        "travel": {"Depot": {"Depot": 0, "A": 1}, "A": {"Depot": 0, "A": 0}},
        "requests": requests if requests is not None else [
            {"id": f"R{i + 1}", "release": 0, "deadline": deadline,
             "region": "A", "category": "generic", "priority": 1, "cancelled": False}
            for i, deadline in enumerate([2, 2, 6, 8])
        ],
        "weights": {"rejection": 200, "lateness": 1, "charge": 1, "fairness": 0},
    }


def solve(case):
    # Delayed import gives a clear failure until the public API exists.
    from dispatch import reference
    from dispatch.checker import validate_schedule
    assert callable(getattr(reference, "exhaustive", None)), "exhaustive API is missing"
    result = reference.exhaustive(case)
    assert validate_schedule(case, result["schedule"]) == []
    return result


def test_four_request_hand_optimum_requires_two_nonoverlapping_recharges():
    result = solve(scenario())
    assert result["objective"] == 2
    assert result["exact"] is True
    assert len(result["schedule"]["services"]) == 4
    charges = sorted(result["schedule"]["charges"], key=lambda item: item["start"])
    assert len(charges) == 2
    assert charges[0]["end"] <= charges[1]["start"]
    assert result["enumerated_states"] > result["enumerated_leaves"] > 0


def test_empty_demand_and_no_resources_have_zero_objective():
    case = scenario([])
    for resource in ("vehicles", "battery_ids", "charger_ids", "technician_ids"):
        case[resource] = []
    result = solve(case)
    assert result["objective"] == 0
    assert result["schedule"]["services"] == []
    assert result["schedule"]["charges"] == []
    assert result["schedule"]["unserved"] == []


def test_horizon_completion_and_half_open_availability_boundary():
    case = scenario()
    case["requests"] = case["requests"][:1]
    case["requests"][0]["release"] = 6
    case["requests"][0]["deadline"] = 8
    case["vehicles"] = [{"id": "V1", "unavailable": [[0, 6]]}]
    result = solve(case)
    assert result["objective"] == 0
    assert result["schedule"]["services"][0]["start"] == 6
    assert result["schedule"]["services"][0]["end"] == 8
    case["requests"][0]["release"] = 7
    assert solve(case)["objective"] == 200


def test_cancelled_requests_excluded_from_rejection_and_fairness():
    case = scenario()
    case["vehicles"] = []
    case["requests"][0]["cancelled"] = True
    case["requests"][0]["priority"] = 50
    case["weights"]["fairness"] = 9
    result = solve(case)
    assert result["objective"] == 609
    assert [record["status"] for record in result["schedule"]["unserved"]].count("cancelled") == 1


def test_deliberate_rejection_when_lateness_cost_exceeds_penalty():
    case = scenario()
    case["requests"] = case["requests"][:1]
    case["requests"][0]["deadline"] = 0
    case["weights"]["rejection"] = 1
    result = solve(case)
    assert result["objective"] == 1
    assert result["schedule"]["services"] == []
    assert result["schedule"]["unserved"][0]["status"] == "rejected"


def test_slot_minutes_priority_and_region_fairness_are_independent_terms():
    case = scenario()
    case["requests"] = case["requests"][:2]
    case["requests"][0].update(priority=3, deadline=1)
    case["requests"][1].update(region="B", release=8, priority=2)
    case["travel"]["Depot"]["B"] = 1
    case["travel"]["B"] = {"Depot": 0, "A": 0, "B": 0}
    case["travel"]["A"]["B"] = 0
    case["slot_minutes"] = 5
    case["weights"] = {"rejection": 100, "lateness": 2, "charge": 1, "fairness": 7}
    # R1: 3 * one late slot * 5 minutes * 2. R2: 2 * 100.
    # Region B is wholly rejected: max regional fraction = 1.
    assert solve(case)["objective"] == 237


def test_idle_is_needed_to_keep_battery_for_a_future_high_priority_request():
    case = scenario()
    case["requests"] = case["requests"][:2]
    case["requests"][0].update(deadline=8, priority=1)
    case["requests"][1].update(release=1, deadline=3, priority=10)
    case["battery_ids"] = ["B1"]
    case["charger_ids"] = []
    result = solve(case)
    assert result["objective"] == 200
    assert [record["request_id"] for record in result["schedule"]["services"]] == ["R2"]
    assert result["schedule"]["services"][0]["start"] == 1


def test_calendar_distinguishes_otherwise_identical_vehicles():
    case = scenario()
    case["requests"] = case["requests"][:2]
    case["requests"][0].update(release=0, deadline=3)
    case["requests"][1].update(release=1, deadline=3)
    case["vehicles"][0]["unavailable"] = [[0, 1]]
    case["vehicles"][1]["unavailable"] = [[3, 8]]
    result = solve(case)
    assert result["objective"] == 0
    assert len(result["schedule"]["services"]) == 2


def test_input_is_not_mutated_and_guard_rejects_large_instances():
    case = scenario([])
    before = deepcopy(case)
    solve(case)
    assert case == before
    case["horizon"] = 9
    with pytest.raises(ValueError, match="tiny"):
        solve(case)


@pytest.mark.parametrize(("change", "optimum", "served_count"), [
    ({"charger_ids": []}, 400, 2),
    ({"battery_ids": []}, 800, 0),
    ({"technician_ids": ["T1"]}, 201, 3),
    ({"technician_ids": []}, 800, 0),
    ({"horizon": 6}, 201, 3),
    ({"horizon": 6, "charger_ids": ["C1", "C2"]}, 2, 4),
])
def test_hand_variants_have_independently_calculated_optima(change, optimum, served_count):
    case = scenario()
    case.update(change)
    result = solve(case)
    assert result["objective"] == optimum
    assert len(result["schedule"]["services"]) == served_count


def test_expensive_recharge_can_be_rejected_in_favor_of_unserved_demand():
    case = scenario()
    case["weights"]["charge"] = 250
    result = solve(case)
    assert result["objective"] == 400
    assert result["schedule"]["charges"] == []


def test_fractional_fairness_optimum_is_compared_exactly():
    case = scenario()
    case["weights"] = {"rejection": 0, "lateness": 0, "charge": 3, "fairness": 10}
    result = solve(case)
    # Two initial batteries + one recharge serve three requests: 3 + 10/4.
    # Two recharges cost 6; serving only two gives fairness cost 5 and wins.
    assert result["objective"] == 5
    assert result["objective_rational"] == "5"
    case["weights"]["charge"] = 2
    case["horizon"] = 6
    # Only three services fit: one recharge plus 1/4 regional rejection.
    result = solve(case)
    assert result["objective"] == 4.5
    assert result["objective_rational"] == "9/2"
