"""Independent JSON feasibility checker; standard-library dependencies only.

This module deliberately imports no simulator, optimizer, model, or objective
helpers. It reconstructs durations, intervals, and battery state transitions
directly from the published interchange contract. Solver metadata is not proof
of feasibility or optimality and is not trusted by this checker.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _string(value):
    return isinstance(value, str) and bool(value.strip())


def _schema(scenario, schedule):
    """Reject malformed JSON before feasibility arithmetic or ID lookup."""
    errors = []
    if not isinstance(scenario, dict) or not isinstance(schedule, dict):
        return ["scenario and schedule must be JSON objects"]

    def require(record, fields, label):
        for name, predicate in fields.items():
            if name not in record or not predicate(record[name]):
                errors.append(f"{label}.{name}: missing or invalid value")

    def unique_ids(values, label):
        if not isinstance(values, list):
            errors.append(f"{label}: expected list")
            return
        if any(not _string(value) for value in values):
            errors.append(f"{label}: IDs must be nonempty strings")
        elif len(values) != len(set(values)):
            errors.append(f"{label}: duplicate IDs")

    require(scenario, {
        "id": _string, "seed": lambda x: type(x) is int,
        "horizon": lambda x: _integer(x, 1),
        "slot_minutes": lambda x: _integer(x, 1),
        "load_time": lambda x: _integer(x, 1),
        "handoff_time": _integer, "turnaround_time": _integer,
        "charge_duration": lambda x: _integer(x, 1),
        "vehicles": lambda x: isinstance(x, list),
        "requests": lambda x: isinstance(x, list),
        "travel": lambda x: isinstance(x, dict),
        "weights": lambda x: isinstance(x, dict),
    }, "scenario")
    for key in ("battery_ids", "charger_ids", "technician_ids"):
        unique_ids(scenario.get(key), f"scenario.{key}")

    vehicles = scenario.get("vehicles", [])
    if isinstance(vehicles, list):
        ids = []
        for i, vehicle in enumerate(vehicles):
            label = f"scenario.vehicles[{i}]"
            if not isinstance(vehicle, dict):
                errors.append(f"{label}: expected object")
                continue
            require(vehicle, {"id": _string, "unavailable": lambda x: isinstance(x, list)}, label)
            ids.append(vehicle.get("id"))
            if isinstance(vehicle.get("unavailable"), list):
                for interval in vehicle["unavailable"]:
                    if not (isinstance(interval, list) and len(interval) == 2
                            and all(_integer(t) for t in interval)
                            and interval[0] < interval[1]):
                        errors.append(f"{label}.unavailable: expected [start,end] with 0 <= start < end")
        unique_ids(ids, "scenario.vehicles IDs")

    regions = {"Depot"}
    requests = scenario.get("requests", [])
    if isinstance(requests, list):
        ids = []
        for i, request in enumerate(requests):
            label = f"scenario.requests[{i}]"
            if not isinstance(request, dict):
                errors.append(f"{label}: expected object")
                continue
            require(request, {
                "id": _string, "release": _integer, "deadline": _integer,
                "region": _string, "category": _string,
                "priority": lambda x: _integer(x, 1),
                "cancelled": lambda x: type(x) is bool,
            }, label)
            ids.append(request.get("id"))
            if _string(request.get("region")):
                regions.add(request["region"])
        unique_ids(ids, "scenario.requests IDs")

    travel = scenario.get("travel")
    if isinstance(travel, dict):
        for region in regions:
            row = travel.get(region)
            if not isinstance(row, dict):
                errors.append(f"scenario.travel.{region}: missing matrix row")
                continue
            for destination in regions:
                if not _integer(row.get(destination)):
                    errors.append(f"scenario.travel.{region}.{destination}: expected nonnegative integer")
        for region, row in travel.items():
            if not _string(region) or not isinstance(row, dict):
                errors.append("scenario.travel: invalid matrix row")
                continue
            for destination, duration in row.items():
                if not _string(destination) or not _integer(duration):
                    errors.append(f"scenario.travel.{region}: invalid destination or duration")

    weights = scenario.get("weights")
    if isinstance(weights, dict):
        def weight(value):
            return (type(value) is int and value >= 0) or (type(value) is float and math.isfinite(value) and value >= 0)
        require(weights, dict.fromkeys(("rejection", "lateness", "charge", "fairness"), weight), "scenario.weights")

    require(schedule, {
        "scenario_id": _string, "policy": _string,
        "information": lambda x: isinstance(x, str) and x in ("offline", "online"),
        "services": lambda x: isinstance(x, list),
        "charges": lambda x: isinstance(x, list),
        "unserved": lambda x: isinstance(x, list),
        "solver": lambda x: isinstance(x, dict),
    }, "schedule")
    schemas = {
        "services": {**dict.fromkeys(("request_id", "vehicle_id", "battery_id", "technician_id"), _string),
                     **dict.fromkeys(("start", "delivery", "end"), _integer)},
        "charges": {**dict.fromkeys(("battery_id", "charger_id", "technician_id"), _string),
                    **dict.fromkeys(("start", "end"), _integer)},
        "unserved": {"request_id": _string, "reason": _string,
                     "status": lambda x: isinstance(x, str) and x in ("cancelled", "rejected")},
    }
    for key, fields in schemas.items():
        records = schedule.get(key)
        if isinstance(records, list):
            for i, record in enumerate(records):
                label = f"schedule.{key}[{i}]"
                if not isinstance(record, dict):
                    errors.append(f"{label}: expected object")
                else:
                    require(record, fields, label)
    return errors


def validate_schedule(scenario: dict, schedule: dict) -> list[str]:
    """Return an empty list iff the JSON schedule is structurally and physically valid.

    Deadlines are soft and do not invalidate a service. The result establishes
    feasibility only: it does not verify objective values, optimality claims,
    or whether an online decision process had access to future information.
    """
    errors = _schema(scenario, schedule)
    if errors:
        return errors
    if schedule["scenario_id"] != scenario["id"]:
        errors.append("schedule.scenario_id does not match scenario.id")

    requests = {record["id"]: record for record in scenario["requests"]}
    vehicles = {record["id"]: record for record in scenario["vehicles"]}
    known = {"request_id": set(requests), "vehicle_id": set(vehicles),
             "battery_id": set(scenario["battery_ids"]),
             "charger_id": set(scenario["charger_ids"]),
             "technician_id": set(scenario["technician_ids"])}
    for collection in ("services", "charges", "unserved"):
        for i, record in enumerate(schedule[collection]):
            for key, ids in known.items():
                if key in record and record[key] not in ids:
                    errors.append(f"{collection}[{i}]: unknown {key} {record[key]!r}")
    if errors:
        return errors

    occurrences = Counter(record["request_id"] for record in schedule["services"] + schedule["unserved"])
    for request_id in requests:
        if occurrences[request_id] != 1:
            errors.append(f"request {request_id}: must occur exactly once, found {occurrences[request_id]}")
    for record in schedule["unserved"]:
        cancelled = requests[record["request_id"]]["cancelled"]
        if (record["status"] == "cancelled") != cancelled:
            errors.append(f"request {record['request_id']}: unserved status disagrees with administrative cancellation")

    intervals = defaultdict(list)
    battery_events = defaultdict(list)
    horizon = scenario["horizon"]

    def reserve(kind, resource_id, start, end, label):
        intervals[(kind, resource_id)].append((start, end, label))

    for i, service in enumerate(schedule["services"]):
        request_id = service["request_id"]
        request = requests[request_id]
        label = f"service {request_id} (record {i})"
        start = service["start"]
        # Derive every release independently; exported delivery/end are assertions.
        delivery = start + scenario["load_time"] + scenario["travel"]["Depot"][request["region"]] + scenario["handoff_time"]
        end = delivery + scenario["travel"][request["region"]]["Depot"] + scenario["turnaround_time"]
        if service["delivery"] != delivery or service["end"] != end:
            errors.append(f"{label}: delivery/end disagree with independently derived {delivery}/{end}")
        if request["cancelled"]:
            errors.append(f"{label}: cancelled request must not be served")
        if start < request["release"]:
            errors.append(f"{label}: starts before request release")
        if end > horizon:
            errors.append(f"{label}: completion exceeds horizon")
        vehicle_id, battery_id = service["vehicle_id"], service["battery_id"]
        reserve("vehicle", vehicle_id, start, end, label)
        reserve("battery", battery_id, start, end, label)
        reserve("technician", service["technician_id"], start, start + scenario["load_time"], label)
        for blocked_start, blocked_end in vehicles[vehicle_id]["unavailable"]:
            if start < blocked_end and blocked_start < end:
                errors.append(f"{label}: overlaps vehicle {vehicle_id} unavailability [{blocked_start},{blocked_end})")
        battery_events[battery_id].extend([(start, 1, "service_start", label), (end, 0, "service_end", label)])

    for i, charge in enumerate(schedule["charges"]):
        label = f"charge {i}"
        start = charge["start"]
        end = start + scenario["charge_duration"]
        if charge["end"] != end:
            errors.append(f"{label}: end disagrees with independently derived {end}")
        if end > horizon:
            errors.append(f"{label}: completion exceeds horizon")
        for kind in ("battery", "charger", "technician"):
            reserve(kind, charge[f"{kind}_id"], start, end, label)
        battery_events[charge["battery_id"]].extend([(start, 1, "charge_start", label), (end, 0, "charge_end", label)])

    for (kind, resource_id), reservations in sorted(intervals.items()):
        previous_end, previous_label = -1, ""
        for start, end, label in sorted(reservations):
            if start < previous_end:
                errors.append(f"{kind} {resource_id}: {label} overlaps {previous_label}")
            if end > previous_end:
                previous_end, previous_label = end, label

    transitions = {"service_start": ("full", "in_service"), "service_end": ("in_service", "depleted"),
                   "charge_start": ("depleted", "charging"), "charge_end": ("charging", "full")}
    for battery_id, events in sorted(battery_events.items()):
        state, active = "full", None
        # Sorting completion priority 0 before start priority 1 gives half-open semantics.
        for time, priority, operation, label in sorted(events):
            expected, next_state = transitions[operation]
            if state != expected or (priority == 0 and active != label):
                errors.append(f"battery {battery_id} at {time}: {operation} for {label} requires {expected}, found {state}")
            state = next_state
            active = label if priority == 1 else None
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Independently validate a medical dispatch JSON schedule")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("schedule", type=Path)
    args = parser.parse_args(argv)
    try:
        scenario = json.loads(args.scenario.read_text())
        schedule = json.loads(args.schedule.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"INVALID: unable to read JSON: {error}")
        return 2
    errors = validate_schedule(scenario, schedule)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"VALID: {schedule['scenario_id']} / {schedule['policy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
