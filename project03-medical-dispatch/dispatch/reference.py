"""Independent exhaustive reference for the integer-slot scheduling contract.

This module imports only the Python standard library. It neither shares the
optimizer's formulation nor calls the simulator or feasibility checker.

Exactness argument for the bounded input class:
* At each integer slot, recursively enumerate each feasible set of new services
  and recharges, including the empty set. All operations have positive duration,
  so simultaneous starts commute. Ordering starts lexicographically removes
  permutations of the same action set, without removing a possible schedule.
* Unselected requests remain available. At the horizon they are rejected. Thus
  idling and deliberate rejection are included, even when service is feasible.
* Currently idle full batteries, depleted batteries, chargers and technicians
  are interchangeable. Select the first available identifier of each kind.
  Idle vehicles are interchangeable only when their complete unavailability
  calendars match. Swapping the future labels of equivalent idle resources
  preserves feasibility and every objective term; each labeled schedule has
  a representative in the enumeration. Busy resources are never merged.
* Time, served-request mask, resource release times and battery energy after
  release determine all future feasibility and costs. Memoizing that state is
  exact. Previously accrued additive costs are charged on transitions; rejection
  and regional fairness depend only on the final served mask.

The reported state/leaf counts are unique memoized states after the above
symmetry reductions, not counts of all labeled schedules. Decimal input weights
are converted through their text representation to rational numbers, avoiding
floating-point comparisons during minimization. Guards fail explicitly rather
than returning a truncated search as exact.
"""

from collections import Counter
from fractions import Fraction
from functools import lru_cache
from time import perf_counter


def exhaustive(scenario: dict) -> dict:
    """Return an exact optimum and witness for <=4 requests, horizon <=8.

    Each resource pool may have at most two members. Empty pools and cancelled
    demand are allowed. Raises ValueError for malformed/out-of-scope inputs and
    RuntimeError if the explicit one-million-state/five-million-edge guard is
    exceeded; a guard exception makes no optimality claim.
    """
    started = perf_counter()

    def integer(value, name, minimum=0):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
        return value

    horizon = integer(scenario["horizon"], "horizon", 1)
    requests_all = scenario["requests"]
    if horizon > 8 or len(requests_all) > 4:
        raise ValueError("tiny reference supports horizon <= 8 and <= 4 requests")
    load = integer(scenario["load_time"], "load_time", 1)
    handoff = integer(scenario["handoff_time"], "handoff_time")
    turnaround = integer(scenario["turnaround_time"], "turnaround_time")
    charge_duration = integer(scenario["charge_duration"], "charge_duration", 1)
    minutes = integer(scenario["slot_minutes"], "slot_minutes", 1)
    vehicles = scenario["vehicles"]
    vehicle_ids = [vehicle["id"] for vehicle in vehicles]
    battery_ids = scenario["battery_ids"]
    charger_ids = scenario["charger_ids"]
    technician_ids = scenario["technician_ids"]
    for name, ids in (("vehicles", vehicle_ids), ("battery_ids", battery_ids),
                      ("charger_ids", charger_ids), ("technician_ids", technician_ids)):
        if len(ids) > 2:
            raise ValueError(f"tiny reference supports <= 2 {name}")
        if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"{name} must have unique nonempty string identifiers")
    calendars = []
    for vehicle in vehicles:
        intervals = []
        for pair in vehicle["unavailable"]:
            if len(pair) != 2:
                raise ValueError("vehicle unavailability must contain [start, end] pairs")
            begin = integer(pair[0], "unavailability start")
            end = integer(pair[1], "unavailability end")
            if end <= begin:
                raise ValueError("unavailability end must follow start")
            intervals.append((begin, end))
        calendars.append(tuple(sorted(intervals)))

    seen = set()
    requests = []
    for request in requests_all:
        identity = request["id"]
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("request identifiers must be unique nonempty strings")
        seen.add(identity)
        integer(request["release"], "release")
        integer(request["deadline"], "deadline")
        integer(request["priority"], "priority", 1)
        if type(request["cancelled"]) is not bool:
            raise ValueError("cancelled must be boolean")
        region = request["region"]
        outbound = integer(scenario["travel"]["Depot"][region], "outbound travel")
        inbound = integer(scenario["travel"][region]["Depot"], "inbound travel")
        if not request["cancelled"]:
            requests.append((request, load + outbound + handoff,
                             load + outbound + handoff + inbound + turnaround))

    weights = {}
    for name in ("rejection", "lateness", "charge", "fairness"):
        try:
            value = Fraction(str(scenario["weights"][name]))
        except (ValueError, ZeroDivisionError) as error:
            raise ValueError(f"{name} weight must be finite and nonnegative") from error
        if value < 0:
            raise ValueError(f"{name} weight must be nonnegative")
        weights[name] = value
    regional_totals = Counter(request["region"] for request, _, _ in requests)
    n = len(requests)
    terminal_cost = {}
    for mask in range(1 << n):
        rejected = [request for q, (request, _, _) in enumerate(requests) if not mask & (1 << q)]
        regional_rejected = Counter(request["region"] for request in rejected)
        worst = max((Fraction(regional_rejected[region], count)
                     for region, count in regional_totals.items()), default=Fraction(0))
        terminal_cost[mask] = (
            weights["rejection"] * sum(request["priority"] for request in rejected)
            + weights["fairness"] * worst
        )

    # State: time, served mask, vehicle releases, (battery release, full-after)
    # pairs, charger releases, technician releases. Releases <= time become 0.
    initial = (0, 0, (0,) * len(vehicles), ((0, 1),) * len(battery_ids),
               (0,) * len(charger_ids), (0,) * len(technician_ids))
    best_choices = {}
    counts = {"states": 0, "leaves": 0, "transitions": 0}

    def successors(state):
        time, served, vehicle_free, batteries, charger_free, technician_free = state

        def starts(mask, vf, bs, cf, tf, after, cost, actions):
            # Ending this simultaneous-start set is always allowed: deliberate
            # idling never needs an artificial action or penalty.
            next_time = time + 1
            next_state = (
                next_time, mask,
                tuple(value if value > next_time else 0 for value in vf),
                tuple((value if value > next_time else 0, full) for value, full in bs),
                tuple(value if value > next_time else 0 for value in cf),
                tuple(value if value > next_time else 0 for value in tf),
            )
            yield next_state, cost, actions
            technician = next((i for i, release in enumerate(tf) if release <= time), None)
            if technician is None:
                return
            battery = next((i for i, (release, full) in enumerate(bs)
                            if release <= time and full), None)
            if battery is not None:
                for q, (request, delivery_duration, mission_duration) in enumerate(requests):
                    if mask & (1 << q) or request["release"] > time:
                        continue
                    delivery = time + delivery_duration
                    end = time + mission_duration
                    if end > horizon:
                        continue
                    used_calendars = set()
                    for vehicle, release in enumerate(vf):
                        if release > time or calendars[vehicle] in used_calendars:
                            continue
                        used_calendars.add(calendars[vehicle])
                        if any(time < stop and begin < end for begin, stop in calendars[vehicle]):
                            continue
                        action = (0, q, vehicle, battery, technician)
                        if action <= after:
                            continue
                        new_vf, new_bs, new_tf = list(vf), list(bs), list(tf)
                        new_vf[vehicle] = end
                        new_bs[battery] = (end, 0)
                        new_tf[technician] = time + load
                        penalty = (weights["lateness"] * request["priority"]
                                   * max(delivery - request["deadline"], 0) * minutes)
                        yield from starts(mask | (1 << q), tuple(new_vf), tuple(new_bs), cf,
                                          tuple(new_tf), action, cost + penalty, actions + (action,))
            battery = next((i for i, (release, full) in enumerate(bs)
                            if release <= time and not full), None)
            charger = next((i for i, release in enumerate(cf) if release <= time), None)
            if battery is not None and charger is not None and time + charge_duration <= horizon:
                action = (1, battery, charger, technician)
                if action > after:
                    end = time + charge_duration
                    new_bs, new_cf, new_tf = list(bs), list(cf), list(tf)
                    new_bs[battery] = (end, 1)
                    new_cf[charger] = end
                    new_tf[technician] = end
                    yield from starts(mask, vf, tuple(new_bs), tuple(new_cf), tuple(new_tf),
                                      action, cost + weights["charge"], actions + (action,))

        yield from starts(served, vehicle_free, batteries, charger_free, technician_free,
                          (-1,), Fraction(0), ())

    @lru_cache(maxsize=None)
    def value(state):
        counts["states"] += 1
        if counts["states"] > 1_000_000:
            raise RuntimeError("tiny exhaustive reference exceeded its 1,000,000-state guard")
        if state[0] == horizon:
            counts["leaves"] += 1
            return terminal_cost[state[1]]
        best = None
        choice = None
        for next_state, cost, actions in successors(state):
            counts["transitions"] += 1
            if counts["transitions"] > 5_000_000:
                raise RuntimeError("tiny exhaustive reference exceeded its 5,000,000-transition guard")
            candidate = cost + value(next_state)
            if best is None or candidate < best:
                best = candidate
                choice = (actions, next_state)
        best_choices[state] = choice
        return best

    optimum = value(initial)
    services = []
    charges = []
    state = initial
    while state[0] < horizon:
        actions, next_state = best_choices[state]
        time = state[0]
        for action in actions:
            if action[0] == 0:
                _, q, vehicle, battery, technician = action
                request, delivery_duration, mission_duration = requests[q]
                services.append({
                    "request_id": request["id"], "vehicle_id": vehicle_ids[vehicle],
                    "battery_id": battery_ids[battery], "technician_id": technician_ids[technician],
                    "start": time, "delivery": time + delivery_duration, "end": time + mission_duration,
                })
            else:
                _, battery, charger, technician = action
                charges.append({
                    "battery_id": battery_ids[battery], "charger_id": charger_ids[charger],
                    "technician_id": technician_ids[technician], "start": time,
                    "end": time + charge_duration,
                })
        state = next_state
    served_ids = {service["request_id"] for service in services}
    unserved = [
        {"request_id": request["id"],
         "status": "cancelled" if request["cancelled"] else "rejected",
         "reason": "administrative cancellation" if request["cancelled"] else "exhaustive optimum selection"}
        for request in requests_all if request["id"] not in served_ids
    ]
    metadata = {
        "status": "OPTIMAL", "method": "exhaustive integer-slot state enumeration",
        "objective": float(optimum), "objective_rational": str(optimum),
        "best_bound": float(optimum), "gap": 0.0, "exact": True,
        "enumerated_states": counts["states"], "enumerated_leaves": counts["leaves"],
        "transitions": counts["transitions"], "cache_hits": value.cache_info().hits,
        "count_semantics": "unique states after idle-resource symmetry reduction; leaves are horizon states",
        "runtime_seconds": perf_counter() - started,
    }
    schedule = {"scenario_id": scenario["id"], "policy": "exhaustive-reference",
                "information": "offline", "services": services, "charges": charges,
                "unserved": unserved, "solver": metadata.copy()}
    return {**metadata, "schedule": schedule}
