"""Deterministic, non-preemptive FCFS and EDF discrete-event dispatch.

Every event at a clock value is applied before any new acquisition. Policy
state contains only released requests, even when the input is labelled offline.
The offline heuristics deliberately use the same myopic rules as their online
counterparts; the optimization model can exploit advance demand information.
"""

from copy import deepcopy
import heapq
from itertools import count

from .schema import durations, validate_scenario


class _Dispatcher:
    """Resource state and policy, without access to unrevealed demand."""

    def __init__(self, configuration, policy, information):
        self.s = configuration
        self.policy = policy
        self.information = information
        self.horizon = configuration["horizon"]
        self.vehicles = {v["id"]: v for v in configuration["vehicles"]}
        self.free_vehicles = set(self.vehicles)
        self.full_batteries = set(configuration["battery_ids"])
        self.free_chargers = set(configuration["charger_ids"])
        self.free_technicians = set(configuration["technician_ids"])
        self.depleted = []  # (actual return time, battery id)
        self.pending = {}
        self.visible = set()
        self.cancelled = set()
        self.events = []
        self.sequence = count()
        self.services = []
        self.charges = []
        self.decisions = []
        self.event_count = 0

    def event(self, time, kind, payload=None):
        heapq.heappush(self.events, (time, next(self.sequence), kind, payload))

    def _apply_event(self, time, kind, payload):
        if kind == "request_release":
            # The arrival event is the only demand entry point for the policy.
            request = payload
            self.visible.add(request["id"])
            if request["cancelled"]:
                self.cancelled.add(request["id"])
            else:
                self.pending[request["id"]] = request
        elif kind == "resource_return":
            vehicle, battery = payload
            self.free_vehicles.add(vehicle)
            heapq.heappush(self.depleted, (time, battery))
        elif kind == "loading_complete":
            self.free_technicians.add(payload)
        elif kind == "charge_complete":
            battery, charger, technician = payload
            self.full_batteries.add(battery)
            self.free_chargers.add(charger)
            self.free_technicians.add(technician)
        # Availability boundaries and the horizon are wake-up events only.
        # Availability is checked over the whole proposed vehicle interval.

    def _request_key(self, request):
        if self.policy == "edf":
            return request["deadline"], request["release"], request["id"]
        return request["release"], request["id"]

    def _available(self, vehicle, start, end):
        return all(end <= a or b <= start
                   for a, b in self.vehicles[vehicle]["unavailable"])

    def _acquire(self, time):
        service_starts = []
        charge_starts = []
        # Scan the whole queue: an infeasible head does not block later work.
        for request in sorted(self.pending.values(), key=self._request_key):
            if not self.full_batteries or not self.free_technicians:
                break
            delivery_offset, end_offset = durations(self.s, request)
            end = time + end_offset
            if end > self.horizon:
                continue
            vehicle = next((v for v in sorted(self.free_vehicles)
                            if self._available(v, time, end)), None)
            if vehicle is None:
                continue
            battery = min(self.full_batteries)
            technician = min(self.free_technicians)
            service = {
                "request_id": request["id"], "vehicle_id": vehicle,
                "battery_id": battery, "technician_id": technician,
                "start": time, "delivery": time + delivery_offset, "end": end,
            }
            self.services.append(service)
            service_starts.append(dict(service))
            self.free_vehicles.remove(vehicle)
            self.full_batteries.remove(battery)
            self.free_technicians.remove(technician)
            del self.pending[request["id"]]
            self.event(time + self.s["load_time"], "loading_complete", technician)
            self.event(end, "resource_return", (vehicle, battery))

        # Service starts have priority over charging. Proactive FIFO charging
        # does not consult pending demand or any unrevealed arrivals. It may
        # therefore make a terminal recharge that the optimizer would omit.
        charge_end = time + self.s["charge_duration"]
        while (self.depleted and self.free_chargers and self.free_technicians
               and charge_end <= self.horizon):
            _, battery = heapq.heappop(self.depleted)
            charger = min(self.free_chargers)
            technician = min(self.free_technicians)
            charge = {"battery_id": battery, "charger_id": charger,
                      "technician_id": technician, "start": time,
                      "end": charge_end}
            self.charges.append(charge)
            charge_starts.append(dict(charge))
            self.free_chargers.remove(charger)
            self.free_technicians.remove(technician)
            self.event(charge_end, "charge_complete", (battery, charger, technician))

        self.decisions.append({
            "time": time, "visible_request_ids": sorted(self.visible),
            "service_starts": service_starts, "charge_starts": charge_starts,
        })

    def run(self):
        while self.events and self.events[0][0] <= self.horizon:
            time = self.events[0][0]
            # Grouping ensures every release precedes same-time acquisition,
            # independently of the event insertion order.
            while self.events and self.events[0][0] == time:
                _, _, kind, payload = heapq.heappop(self.events)
                self._apply_event(time, kind, payload)
                self.event_count += 1
            self._acquire(time)

    def rejection_reason(self, request):
        """Post-run explanation; this function cannot affect policy actions."""
        if request["release"] >= self.horizon:
            return "Request release leaves no service time within the horizon"
        if not self.vehicles:
            return "No vehicle is configured"
        if not self.s["battery_ids"]:
            return "No battery is configured"
        if not self.s["technician_ids"]:
            return "No technician is configured for loading"
        _, length = durations(self.s, request)
        if request["release"] + length > self.horizon:
            return "Complete service including return cannot fit within the horizon"
        calendar_possible = False
        for vehicle in self.vehicles.values():
            candidate = request["release"]
            for start, end in sorted(vehicle["unavailable"]):
                if end <= candidate:
                    continue
                if candidate + length <= start:
                    break
                candidate = end
            if candidate + length <= self.horizon:
                calendar_possible = True
                break
        if not calendar_possible:
            return "No vehicle availability window fits the complete service"
        if not self.s["charger_ids"] and not self.full_batteries:
            return "Initial full batteries exhausted and no charger is configured"
        return "Resource contention under this policy left no feasible start before the horizon"


def simulate(scenario, policy="fcfs", information="offline"):
    """Return a complete deterministic schedule using FCFS or EDF.

    Both heuristics select from released requests only and bypass an infeasible
    queue head. Resource IDs break assignment ties. A battery enters the FIFO
    recharge queue at resource return, never at departure. Charges supervise a
    technician for their entire duration. Idle depleted batteries are recharged
    whenever resources permit and completion fits the horizon, even with no
    current requests. This declared proactive rule is the same in both modes.

    The driver owns future arrivals; the dispatcher receives them exclusively
    as events. Final unserved reporting reads the complete input after all
    decisions are fixed, including requests released beyond the horizon.
    """
    if policy not in {"fcfs", "edf"}:
        raise ValueError("policy must be 'fcfs' or 'edf'")
    if information not in {"offline", "online"}:
        raise ValueError("information must be 'offline' or 'online'")
    validate_scenario(scenario)
    configuration = deepcopy({k: v for k, v in scenario.items() if k != "requests"})
    dispatcher = _Dispatcher(configuration, policy, information)
    dispatcher.event(0, "initial")
    dispatcher.event(scenario["horizon"], "horizon")
    for vehicle in sorted(scenario["vehicles"], key=lambda v: v["id"]):
        for start, end in vehicle["unavailable"]:
            dispatcher.event(start, "availability_boundary")
            dispatcher.event(end, "availability_boundary")
    for request in sorted(scenario["requests"], key=lambda r: (r["release"], r["id"])):
        dispatcher.event(request["release"], "request_release", deepcopy(request))
    dispatcher.run()

    served = {service["request_id"] for service in dispatcher.services}
    unserved = []
    for request in sorted(scenario["requests"], key=lambda r: r["id"]):
        if request["id"] in served:
            continue
        cancelled = request["cancelled"]
        reason = ("Administrative pre-dispatch cancellation supplied with the request"
                  if cancelled else dispatcher.rejection_reason(request))
        unserved.append({"request_id": request["id"],
                         "status": "cancelled" if cancelled else "rejected",
                         "reason": reason})
    return {
        "scenario_id": scenario["id"], "policy": policy,
        "information": information, "services": dispatcher.services,
        "charges": dispatcher.charges, "unserved": unserved,
        "decisions": dispatcher.decisions,
        "solver": {
            "status": "HEURISTIC", "optimality_proven": False,
            "method": "discrete_event", "event_count": dispatcher.event_count,
            "head_of_line_bypass": True,
            "request_order": "deadline,release,id" if policy == "edf" else "release,id",
            "resource_order": "lexicographic ID",
            "charge_policy": "service first; proactive FIFO by depletion time then battery ID",
            "information_scope": "only released requests are used for decisions",
        },
    }
