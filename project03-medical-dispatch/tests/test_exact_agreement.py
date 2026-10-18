"""MILP claims must agree with independently enumerated tiny problems."""

import pytest

from dispatch.checker import validate_schedule
from dispatch.metrics import summarize
from dispatch.optimize import optimize
from dispatch.reference import exhaustive
from dispatch.tiny_cases import tiny_cases


CASES = list(tiny_cases())


@pytest.mark.parametrize(("name", "scenario"), CASES, ids=[name for name, _ in CASES])
def test_milp_objective_and_bound_match_exhaustive_reference(name, scenario):
    reference = exhaustive(scenario)
    optimized = optimize(scenario, time_limit=5)
    assert validate_schedule(scenario, reference["schedule"]) == []
    assert validate_schedule(scenario, optimized) == []
    # summarize is not used by the enumerator; this also checks the two separate
    # objective implementations against its exact rational transition costs.
    assert summarize(scenario, reference["schedule"])["objective"] == pytest.approx(reference["objective"])
    assert summarize(scenario, optimized)["objective"] == pytest.approx(reference["objective"])
    assert optimized["solver"]["optimal"]
    assert optimized["solver"]["status"] == 0
    assert optimized["solver"]["used_fallback"] is False
    assert optimized["solver"]["lower_bound"] == pytest.approx(reference["objective"])
    assert optimized["solver"]["relative_gap"] == pytest.approx(0, abs=1e-8)
    assert reference["exact"]
    assert reference["enumerated_states"] >= reference["enumerated_leaves"] > 0
    if name == "hand":
        assert reference["objective"] == 2


def test_tiny_cases_are_deterministic_and_independent_mutable_inputs():
    first = list(tiny_cases())
    second = list(tiny_cases())
    assert first == second
    assert len(first) == 17
    assert len({name for name, _ in first}) == len(first)
    first[0][1]["weights"]["charge"] = 999
    assert list(tiny_cases()) == second
