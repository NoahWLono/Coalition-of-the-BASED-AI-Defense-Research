"""Checker tests use hand data and corruption, without solver-derived expectations."""

from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def validate(scenario, schedule):
    assert importlib.util.find_spec("dispatch.checker") is not None, "independent checker not implemented"
    return importlib.import_module("dispatch.checker").validate_schedule(scenario, schedule)


@pytest.fixture
def hand():
    return tuple(json.loads((ROOT / "fixtures" / name).read_text()) for name in ("hand_four.json", "hand_four_schedule.json"))


def test_checker_accepts_hand_solution(hand):
    assert validate(*hand) == []


@pytest.mark.parametrize("mutation", [
    lambda s, q: q["services"][1].update(vehicle_id="V1"),
    lambda s, q: q["services"][1].update(technician_id="T1"),
    lambda s, q: q["charges"][1].update(start=3, end=5),
    lambda s, q: q["charges"][1].update(technician_id="T1"),
    lambda s, q: q["services"][2].update(battery_id="B2"),
    lambda s, q: q["charges"].pop(0),
    lambda s, q: q["charges"][0].update(start=0, end=2),
    lambda s, q: q["charges"].append(dict(q["charges"][0])),
    lambda s, q: q["services"][0].update(delivery=1),
    lambda s, q: q["services"][0].update(end=3),
    lambda s, q: q["charges"][0].update(end=3),
    lambda s, q: s["requests"][0].update(release=1),
    lambda s, q: s.update(horizon=7),
    lambda s, q: s["vehicles"][0].update(unavailable=[[1, 2]]),
    lambda s, q: s["requests"][0].update(cancelled=True),
    lambda s, q: q["services"].pop(),
    lambda s, q: q["services"].append(dict(q["services"][0])),
    lambda s, q: q["unserved"].append({"request_id": "R1", "status": "rejected", "reason": "duplicate"}),
    lambda s, q: q["services"][0].update(request_id="UNKNOWN"),
    lambda s, q: q["services"][0].update(vehicle_id="UNKNOWN"),
    lambda s, q: q["services"][0].update(battery_id="UNKNOWN"),
    lambda s, q: q["services"][0].update(technician_id="UNKNOWN"),
    lambda s, q: q["charges"][0].update(charger_id="UNKNOWN"),
    lambda s, q: q.update(scenario_id="other"),
    lambda s, q: q.update(information="clairvoyant"),
])
def test_rejects_infeasible_or_inconsistent_schedule(hand, mutation):
    scenario, schedule = deepcopy(hand)
    mutation(scenario, schedule)
    assert validate(scenario, schedule)


@pytest.mark.parametrize("bad", [True, 0.5, "0", None, -1, [], {}])
def test_time_requires_nonnegative_integer_excluding_bool(hand, bad):
    scenario, schedule = deepcopy(hand)
    schedule["services"][0]["start"] = bad
    assert validate(scenario, schedule)


@pytest.mark.parametrize("mutation", [
    lambda s, q: s["battery_ids"].append("B1"),
    lambda s, q: s["requests"][0].update(priority=True),
    lambda s, q: s["requests"][0].update(cancelled="false"),
    lambda s, q: s["travel"]["Depot"].update(North=-1),
    lambda s, q: s["travel"]["Depot"].pop("North"),
    lambda s, q: s["weights"].update(charge=float("nan")),
    lambda s, q: s.update(charge_duration=0),
    lambda s, q: s["vehicles"][0].update(unavailable=[[2, 1]]),
    lambda s, q: q.update(services=None),
    lambda s, q: q["services"].append(None),
    lambda s, q: q["services"][0].update(request_id=[]),
    lambda s, q: q["charges"][0].pop("battery_id"),
    lambda s, q: q.pop("solver"),
])
def test_rejects_malformed_records_without_throwing(hand, mutation):
    scenario, schedule = deepcopy(hand)
    mutation(scenario, schedule)
    errors = validate(scenario, schedule)
    assert errors and all(isinstance(error, str) for error in errors)


@pytest.mark.parametrize("scenario,schedule", [(None, None), ([], {}), ({}, []), ({}, {})])
def test_rejects_malformed_top_level(scenario, schedule):
    assert validate(scenario, schedule)


def test_empty_requests_and_zero_resources_are_valid(hand):
    scenario, schedule = deepcopy(hand)
    scenario.update(requests=[], vehicles=[], battery_ids=[], charger_ids=[], technician_ids=[])
    schedule.update(services=[], charges=[], unserved=[])
    assert validate(scenario, schedule) == []


def test_all_rejected_with_zero_resources_is_valid(hand):
    scenario, schedule = deepcopy(hand)
    scenario.update(vehicles=[], battery_ids=[], charger_ids=[], technician_ids=[])
    schedule.update(services=[], charges=[], unserved=[{"request_id": r["id"], "status": "rejected", "reason": "no resources"} for r in scenario["requests"]])
    assert validate(scenario, schedule) == []


@pytest.mark.parametrize("cancelled,status,valid", [(True, "cancelled", True), (True, "rejected", False), (False, "cancelled", False), (False, "rejected", True), (False, "unknown", False)])
def test_cancellation_status_matches_input(hand, cancelled, status, valid):
    scenario, schedule = deepcopy(hand)
    scenario["requests"][3]["cancelled"] = cancelled
    schedule["services"].pop()
    schedule["unserved"].append({"request_id": "R4", "status": status, "reason": "administrative"})
    assert (validate(scenario, schedule) == []) is valid


def test_vehicle_calendar_uses_half_open_intervals(hand):
    scenario, schedule = deepcopy(hand)
    scenario["vehicles"][0]["unavailable"] = [[2, 4]]
    assert validate(scenario, schedule) == []


def test_charge_complete_before_same_time_load_and_depletion_before_charge(hand):
    # The supplied schedule exercises both boundaries at times 2, 4, and 6.
    assert validate(*hand) == []


def test_late_delivery_and_terminal_depleted_batteries_are_allowed(hand):
    scenario, schedule = deepcopy(hand)
    for request in scenario["requests"]:
        request["deadline"] = 0
    assert validate(scenario, schedule) == []


def test_record_order_does_not_affect_validity(hand):
    scenario, schedule = deepcopy(hand)
    schedule["services"].reverse()
    schedule["charges"].reverse()
    assert validate(scenario, schedule) == []


@pytest.mark.parametrize("blocked,valid", [([], True), ([[13, 14]], False), ([[14, 17]], True)])
def test_full_return_interval_includes_handoff_return_and_turnaround(hand, blocked, valid):
    scenario, schedule = deepcopy(hand)
    scenario.update(horizon=20, load_time=2, handoff_time=1, turnaround_time=2)
    scenario["travel"]["Depot"]["North"] = 3
    scenario["travel"]["North"]["Depot"] = 4
    scenario["vehicles"][0]["unavailable"] = blocked
    schedule["services"] = [dict(schedule["services"][0], start=2, delivery=8, end=14)]
    schedule["charges"] = []
    schedule["unserved"] = [{"request_id": f"R{i}", "status": "rejected", "reason": "fixture"} for i in (2, 3, 4)]
    assert (validate(scenario, schedule) == []) is valid


def test_charge_requires_depleted_battery_even_without_other_operations(hand):
    scenario, schedule = deepcopy(hand)
    scenario["requests"] = []
    schedule["services"] = []
    schedule["charges"] = [dict(schedule["charges"][0], start=0, end=2)]
    assert validate(scenario, schedule)


def test_cli_success_and_invalid_exit(hand, tmp_path):
    scenario, schedule = deepcopy(hand)
    sp, qp = tmp_path / "scenario.json", tmp_path / "schedule.json"
    sp.write_text(json.dumps(scenario))
    qp.write_text(json.dumps(schedule))
    command = [sys.executable, "-m", "dispatch.checker", str(sp), str(qp)]
    good = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert good.returncode == 0, good.stdout + good.stderr
    schedule["charges"].clear()
    qp.write_text(json.dumps(schedule))
    bad = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert bad.returncode != 0
    assert "invalid" in (bad.stdout + bad.stderr).lower()


def test_cli_malformed_json_returns_nonzero(tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text("{not json")
    result = subprocess.run([sys.executable, "-m", "dispatch.checker", str(path), str(path)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 2
    assert "INVALID" in result.stdout
