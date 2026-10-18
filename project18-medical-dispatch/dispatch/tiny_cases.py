"""Deterministic synthetic cases for exporting the exact-reference comparison.

The hand fixture plus six named boundary cases and ten seeded variants stay
within four requests, eight integer slots and two resources of each type.
Zero travel is intentional in these abstract reference cases; no geographic
locations or clinical judgments are represented.
"""

from copy import deepcopy
import json
from pathlib import Path
import random


def tiny_cases():
    """Yield fresh ``(name, scenario)`` pairs; random seeds are 18000..18009."""
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "hand_four.json"
    hand = json.loads(fixture.read_text())
    yield "hand", deepcopy(hand)
    for name in ("empty", "no_vehicle", "charger_bottleneck", "staff_bottleneck",
                 "cancelled", "beyond_horizon"):
        case = deepcopy(hand)
        case["id"] = f"tiny-{name}"
        if name == "empty":
            case["requests"] = []
        elif name == "no_vehicle":
            case["vehicles"] = []
            case["weights"]["fairness"] = 7
        elif name == "charger_bottleneck":
            case["horizon"] = 6
            case["weights"].update(rejection=0, charge=2, lateness=0, fairness=10)
        elif name == "staff_bottleneck":
            case["technician_ids"] = case["technician_ids"][:1]
        elif name == "cancelled":
            case["requests"][0]["cancelled"] = True
            case["requests"][0]["priority"] = 20
            case["requests"][-1]["cancelled"] = True
            case["weights"]["fairness"] = 13
        elif name == "beyond_horizon":
            for request in case["requests"]:
                request["release"] = case["horizon"] - 1
        yield name, case

    for seed in range(18000, 18010):
        rng = random.Random(seed)
        horizon = rng.randint(6, 8)
        regions = ("Amber", "Birch")
        travel = {
            "Depot": {"Depot": 0, **{region: rng.randint(0, 2) for region in regions}},
            **{region: {"Depot": rng.randint(0, 1), "Amber": 0, "Birch": 0} for region in regions},
        }
        vehicles = []
        for number in range(rng.randint(1, 2)):
            unavailable = []
            if rng.random() < 0.6:
                start = rng.randrange(horizon)
                unavailable = [[start, min(horizon, start + rng.randint(1, 3))]]
            vehicles.append({"id": f"V{number + 1}", "unavailable": unavailable})
        requests = []
        for number in range(rng.randint(2, 4)):
            release = rng.randint(0, horizon - 2)
            requests.append({
                "id": f"R{number + 1}", "release": release,
                "deadline": rng.randint(release, horizon), "region": rng.choice(regions),
                "category": rng.choice(("package-A", "package-B")),
                "priority": rng.randint(1, 3), "cancelled": rng.random() < 0.15,
            })
        case = {
            "id": f"tiny-seed-{seed}", "seed": seed, "horizon": horizon,
            "slot_minutes": rng.choice((1, 3, 5)), "load_time": rng.randint(1, 2),
            "handoff_time": rng.randint(0, 1), "turnaround_time": rng.randint(0, 1),
            "charge_duration": rng.randint(1, 3), "vehicles": vehicles,
            "battery_ids": [f"B{i + 1}" for i in range(rng.randint(1, 2))],
            "charger_ids": [f"C{i + 1}" for i in range(rng.randint(0, 2))],
            "technician_ids": [f"T{i + 1}" for i in range(rng.randint(1, 2))],
            "travel": travel, "requests": requests,
            "weights": {"rejection": rng.choice((1, 7, 20)),
                        "lateness": rng.choice((0, 0.5, 1, 4)),
                        "charge": rng.choice((0, 1, 5)), "fairness": rng.choice((0, 3, 11))},
        }
        yield f"seed-{seed}", case
