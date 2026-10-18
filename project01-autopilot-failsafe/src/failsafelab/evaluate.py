"""Offline, fail-closed evaluation of sealed MAVLink evidence.

This module never imports the runner. Verdicts come from decoded saved packets;
event records locate actions but cannot prove an aircraft state or fault.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
import math
import operator
from pathlib import Path
import re
import sys
from typing import Any

from pymavlink import mavutil

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "INDETERMINATE"
MAX_SAMPLE_GAP_S = 2.5
EPS = 0.002
COMPARE = {"lt": operator.lt, "le": operator.le, "eq": operator.eq, "ge": operator.ge, "gt": operator.gt}


def _check(name: str, outcome: str, detail: str, **evidence: Any) -> dict:
    return {"id": name, "outcome": outcome, "detail": detail, **evidence}


def _finite(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a time or numeric threshold")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite numeric value")
    return result


def _json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _seal(path: Path, synthetic: bool) -> dict:
    manifest = path / "SHA256SUMS"
    if not manifest.is_file():
        return _check("seal", UNKNOWN, "Required checksum seal SHA256SUMS is missing")
    required = {"scenario.json", "events.jsonl", "run.json", "rx.tlog", "tx.tlog"}
    if not synthetic:
        required |= {"timing.jsonl", "params-before.json", "params-after.json", "sitl.stdout"}
    seen, errors = set(), []
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if not match:
            errors.append("Malformed checksum line")
            continue
        digest, name = match.groups()
        relative = Path(name)
        target = path / relative
        if relative.is_absolute() or ".." in relative.parts or target.is_symlink() or not target.resolve().is_relative_to(path.resolve()):
            errors.append(f"Unsafe checksum path: {name}")
            continue
        if name in seen:
            errors.append(f"Duplicate checksum entry: {name}")
        seen.add(name)
        if not target.is_file():
            errors.append(f"Sealed file missing: {name}")
            continue
        with target.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != digest.lower():
            errors.append(f"Checksum mismatch: {name}")
    if required - seen:
        errors.append("Required evidence absent from checksum seal: " + ", ".join(sorted(required - seen)))
    if not synthetic and not any(name.startswith("logs/") and name.upper().endswith(".BIN") for name in seen):
        errors.append("Raw DataFlash log absent from checksum seal")
    return _check("seal", UNKNOWN if errors else PASS, "; ".join(errors) if errors else "All sealed evidence checksums match", files_verified=len(seen))


def _read_tlog(path: Path, receive: bool) -> tuple[list[dict], list[dict], list[str]]:
    rows, clocks, errors = [], [], []
    current_sim, last_epoch = None, None
    connection = mavutil.mavlink_connection(str(path), dialect="ardupilotmega", robust_parsing=True)
    try:
        while True:
            message = connection.recv_match(blocking=False)
            if message is None:
                break
            kind = message.get_type()
            if kind == "BAD_DATA":
                errors.append(f"Malformed MAVLink packet in {path.name}")
                continue
            epoch = float(message._timestamp)
            if not math.isfinite(epoch) or (last_epoch is not None and epoch < last_epoch - EPS):
                errors.append(f"Invalid or decreasing epoch timestamp in {path.name}")
            last_epoch = epoch
            autopilot = message.get_srcSystem() == 1 and message.get_srcComponent() == 1
            if receive and kind == "SYSTEM_TIME" and autopilot:
                current_sim = float(message.time_boot_ms) / 1000
                if clocks and current_sim < clocks[-1]["sim_s"] - EPS:
                    errors.append("Simulator clock moved backwards")
                clocks.append({"epoch_s": epoch, "sim_s": current_sim})
            rows.append({"epoch_s": epoch, "sim_s": current_sim, "type": kind,
                         "system": message.get_srcSystem(), "component": message.get_srcComponent(),
                         "fields": message.to_dict()})
    finally:
        connection.close()
    if not rows:
        errors.append(f"No decoded messages in {path.name}")
    return rows, clocks, list(dict.fromkeys(errors))


def _coverage(times: list[float], start: float, end: float, multiple: bool = True, max_gap: float = MAX_SAMPLE_GAP_S) -> bool:
    selected = sorted(t for t in times if start - EPS <= t <= end + EPS)
    if len(selected) < (2 if multiple else 1):
        return False
    gaps = [selected[0] - start, end - selected[-1]]
    gaps += [b - a for a, b in zip(selected, selected[1:])]
    return max(gaps, default=0) <= max_gap + EPS


def _window(assertion: dict, events: dict) -> tuple[float, float]:
    event = events[assertion["after"]]
    start = _finite(event["sim_s"]) + _finite(assertion.get("start_s", 0))
    length = _finite(assertion.get("duration_s") if assertion["type"] in {"hold_mode", "heartbeat_gap"} else assertion.get("within_s"))
    if length <= 0 or _finite(assertion.get("start_s", 0)) < 0:
        raise ValueError("Assertion windows must be positive with nonnegative starts")
    return start, start + length


def _assertion(assertion: dict, events: dict, rx: list[dict], tx: list[dict], clocks: list[dict], end: float) -> dict:
    name, kind = assertion.get("id", "unnamed"), assertion.get("type")
    evidence = {"type": kind, "fault_evidence": assertion.get("fault_evidence") is True}
    try:
        start, stop = _window(assertion, events)
        evidence["window_sim_s"] = [start, stop]
    except (KeyError, TypeError, ValueError) as exc:
        return _check(name, UNKNOWN, f"Invalid assertion or event reference: {exc}", **evidence)
    if end + EPS < stop or not _coverage([c["sim_s"] for c in clocks], start, stop):
        return _check(name, UNKNOWN, "Observation ends early or simulator clock coverage is insufficient", **evidence)
    action_epoch = _finite(events[assertion["after"]]["host_unix_us"]) / 1e6
    end_epoch = _finite(events["scenario_end"]["host_unix_us"]) / 1e6
    selected = [r for r in rx if r["sim_s"] is not None and start - EPS <= r["sim_s"] <= stop + EPS and action_epoch <= r["epoch_s"] <= end_epoch]
    selected = [r for r in selected if r["system"] == 1 and r["component"] == 1]
    if kind in {"mode", "hold_mode", "disarmed"}:
        rows = [r for r in selected if r["type"] == "HEARTBEAT"]
        if not rows or not _coverage([r["sim_s"] for r in rows], start, stop):
            return _check(name, UNKNOWN, "Insufficient autopilot heartbeat coverage", **evidence)
        observed = [{"sim_s": r["sim_s"], "mode": r["fields"]["custom_mode"], "armed": bool(r["fields"]["base_mode"] & 128)} for r in rows]
        evidence["observations"] = observed
        if kind == "disarmed":
            matches = [r for r in observed if not r["armed"]]
            passed = bool(matches)
        else:
            allowed = assertion.get("allowed")
            if not isinstance(allowed, list) or not allowed or any(type(mode) is not int for mode in allowed):
                return _check(name, UNKNOWN, "Mode assertion requires a nonempty list of numeric allowed modes", **evidence)
            matches = [r for r in observed if r["mode"] in allowed]
            passed = len(matches) == len(observed) if kind == "hold_mode" else bool(matches)
        if passed:
            evidence["first_match_sim_s"] = matches[0]["sim_s"]
        return _check(name, PASS if passed else FAIL, "Observed requested state" if passed else "Observed states do not satisfy the declared assertion", **evidence)
    if kind == "text":
        if "contains_any" in assertion:
            needles = assertion["contains_any"]
            if "contains" in assertion or not isinstance(needles, list) or not needles or any(not isinstance(item, str) or not item.strip() for item in needles):
                return _check(name, UNKNOWN, "Use either contains or a nonempty contains_any list of nonempty strings", **evidence)
        else:
            contains = assertion.get("contains")
            if not isinstance(contains, str) or not contains.strip():
                return _check(name, UNKNOWN, "Text assertion requires a nonempty search string", **evidence)
            needles = [contains]
        evidence["accepted_substrings"] = needles
        rows = [r for r in selected if r["type"] == "STATUSTEXT"]
        evidence["observations"] = [{"sim_s": r["sim_s"], "text": str(r["fields"]["text"])} for r in rows]
        if not rows:
            return _check(name, UNKNOWN, "No status text evidence in assertion window", **evidence)
        matches = [r for r in rows if any(needle.casefold() in str(r["fields"]["text"]).casefold() for needle in needles)]
        if matches:
            evidence["first_match_sim_s"] = matches[0]["sim_s"]
        return _check(name, PASS if matches else FAIL, "Required status text observed" if matches else "Observed status text does not include the required text", **evidence)
    if kind == "field":
        message, field, op = assertion.get("message"), assertion.get("field"), assertion.get("op")
        if op not in COMPARE:
            return _check(name, UNKNOWN, "Unsupported comparison operator", **evidence)
        try:
            target = _finite(assertion["value"])
            rows = [r for r in selected if r["type"] == message and field in r["fields"]]
            values = [(r["sim_s"], _finite(r["fields"][field])) for r in rows]
            if message == "SYS_STATUS" and field == "voltage_battery":
                values = [(time, value) for time, value in values if value != 65535]
            if message in {"GPS_RAW_INT", "GPS2_RAW"} and field == "fix_type":
                values = [(time, value) for time, value in values if 0 <= value <= 8]
        except (KeyError, ValueError, TypeError):
            return _check(name, UNKNOWN, "Missing or unusable numeric field evidence", **evidence)
        if not values:
            return _check(name, UNKNOWN, "No matching field telemetry in assertion window", **evidence)
        evidence["observations"] = [{"sim_s": time, "value": value} for time, value in values]
        matches = [time for time, value in values if COMPARE[op](value, target)]
        evidence["sensor_coverage"] = _coverage([time for time, _ in values], start, stop)
        evidence["max_sample_gap_s"] = MAX_SAMPLE_GAP_S
        if matches:
            evidence["first_match_sim_s"] = matches[0]
        elif not evidence["sensor_coverage"]:
            return _check(name, UNKNOWN, "Insufficient field telemetry coverage to determine comparison failure", **evidence)
        return _check(name, PASS if matches else FAIL, "Field comparison satisfied" if matches else "Observed field values do not satisfy comparison", **evidence)
    if kind in {"heartbeat_gap", "heartbeat_resumed"}:
        gcs = [r for r in tx if r["system"] == 255 and r["type"] == "HEARTBEAT" and r["fields"].get("type") == 6 and r["sim_s"] is not None]
        # Silence is half-open: heartbeats may resume exactly at its end.
        after_action = [r for r in gcs if action_epoch <= r["epoch_s"] <= end_epoch]
        inside = [r for r in after_action if start - EPS <= r["sim_s"] < stop - EPS] if kind == "heartbeat_gap" else [r for r in after_action if start - EPS <= r["sim_s"] <= stop + EPS]
        evidence["observations"] = [{"sim_s": r["sim_s"], "epoch_s": r["epoch_s"]} for r in inside]
        if kind == "heartbeat_gap":
            before = [r for r in gcs if start - MAX_SAMPLE_GAP_S <= r["sim_s"] <= start + EPS and r["epoch_s"] < action_epoch]
            if not before:
                return _check(name, UNKNOWN, "No recent GCS heartbeat establishes a pre-fault link", **evidence)
            passed = not inside
            return _check(name, PASS if passed else FAIL, "Established GCS heartbeat stream is silent for the entire window" if passed else "GCS heartbeat transmitted inside declared silence window", **evidence)
        if inside:
            evidence["first_match_sim_s"] = inside[0]["sim_s"]
        return _check(name, PASS if inside else FAIL, "GCS heartbeat resumed" if inside else "No GCS heartbeat resumed within deadline", **evidence)
    return _check(name, UNKNOWN, f"Unsupported assertion type: {kind}", **evidence)


def _baseline(spec: dict, event: dict, rx: list[dict]) -> dict:
    pre = spec.get("preconditions", {})
    end = _finite(event["sim_s"])
    duration = _finite(pre.get("stable_for_s", 3))
    if duration <= 0:
        return _check("baseline", UNKNOWN, "Baseline stability interval must be positive")
    start = end - duration
    epoch = _finite(event["host_unix_us"]) / 1e6
    rows = [r for r in rx if r["sim_s"] is not None and start - EPS <= r["sim_s"] <= end + EPS and r["epoch_s"] <= epoch and r["system"] == 1 and r["component"] == 1]
    streams = {kind: [r for r in rows if r["type"] == kind] for kind in ["HEARTBEAT", "GLOBAL_POSITION_INT", "GPS_RAW_INT", "SYS_STATUS"]}
    coverage = {kind: _coverage([r["sim_s"] for r in data], start, end, max_gap=.5) for kind, data in streams.items()}
    hb, position, gps, battery = [streams[kind] for kind in ["HEARTBEAT", "GLOBAL_POSITION_INT", "GPS_RAW_INT", "SYS_STATUS"]]
    altitudes = [r["fields"]["relative_alt"] / 1000 for r in position]
    vertical_speeds = [abs(r["fields"]["vz"]) for r in position]
    fixes = [r["fields"]["fix_type"] for r in gps]
    voltages = [r["fields"]["voltage_battery"] for r in battery]
    stable = {
        "mode_armed": bool(hb) and all(r["fields"]["custom_mode"] == pre.get("mode", 4) and bool(r["fields"]["base_mode"] & 128) == pre.get("armed", True) for r in hb),
        "altitude": bool(altitudes) and all(_finite(pre.get("min_altitude_m", 10.5)) <= altitude <= _finite(pre.get("max_altitude_m", 13.5)) for altitude in altitudes),
        "vertical_speed": bool(vertical_speeds) and all(vz <= _finite(pre.get("max_abs_vz_cm_s", 30)) for vz in vertical_speeds),
        "gps_fix": bool(fixes) and all(pre.get("min_gps_fix", 3) <= fix <= 8 for fix in fixes),
        "battery": bool(voltages) and all(_finite(pre.get("min_battery_mv", 11500)) < voltage < 65535 for voltage in voltages),
    }
    passed = all(coverage.values()) and all(stable.values())
    return _check("baseline", PASS if passed else UNKNOWN,
                  "Continuous stable hover observed before baseline_ready" if passed else "Fresh stable hover baseline is not supported by raw telemetry",
                  window_sim_s=[start, end], max_sample_gap_s=.5, stream_coverage=coverage, conditions=stable,
                  sample_counts={kind: len(data) for kind, data in streams.items()},
                  altitude_range_m=[min(altitudes), max(altitudes)] if altitudes else None,
                  max_abs_vz_cm_s=max(vertical_speeds) if vertical_speeds else None,
                  min_gps_fix=min(fixes) if fixes else None, min_battery_mv=min(voltages) if voltages else None)


def _initial_state_until_event(spec: dict, events: dict, rx: list[dict]) -> dict:
    declared = spec.get("events", [])
    if not declared:
        return _check("initial_state_until_event", PASS, "No scheduled event after baseline")
    first = min((events[event["id"]] for event in declared), key=lambda event: _finite(event["host_unix_us"]))
    baseline = events["baseline_ready"]
    start, stop = _finite(baseline["sim_s"]), _finite(first["sim_s"])
    first_epoch = _finite(first["host_unix_us"]) / 1e6
    baseline_epoch = _finite(baseline["host_unix_us"]) / 1e6
    if stop - start <= EPS and first_epoch >= baseline_epoch:
        return _check("initial_state_until_event", PASS, "First event immediately follows the verified baseline", first_event_id=first["id"], window_sim_s=[start, stop])
    rows = [r for r in rx if r["type"] == "HEARTBEAT" and r["system"] == 1 and r["component"] == 1
            and r["sim_s"] is not None and start - EPS <= r["sim_s"] <= stop + EPS
            and baseline_epoch <= r["epoch_s"] < first_epoch]
    observed = [{"sim_s": r["sim_s"], "mode": r["fields"]["custom_mode"], "armed": bool(r["fields"]["base_mode"] & 128)} for r in rows]
    coverage = _coverage([r["sim_s"] for r in rows], start, stop, multiple=stop - start > .5, max_gap=.5)
    pre = spec.get("preconditions", {})
    unchanged = bool(observed) and all(row["mode"] == pre.get("mode", 4) and row["armed"] == pre.get("armed", True) for row in observed)
    passed = coverage and unchanged
    return _check("initial_state_until_event", PASS if passed else UNKNOWN,
                  "Initial mode and armed state persist until the first event" if passed else "Initial mode/armed preconditions or heartbeat coverage were lost before the first event",
                  first_event_id=first["id"], window_sim_s=[start, stop], max_sample_gap_s=.5,
                  heartbeat_coverage=coverage, initial_state_maintained=unchanged, observations=observed)


def _injection_transport(spec: dict, events: dict, rx: list[dict], tx: list[dict]) -> dict:
    evidence = []
    end_epoch = _finite(events["scenario_end"]["host_unix_us"]) / 1e6
    for event in spec.get("events", []):
        if event.get("kind") != "parameter":
            continue
        recorded = events[event["id"]]
        start = _finite(recorded["sim_s"])
        epoch = _finite(recorded["host_unix_us"]) / 1e6
        value = _finite(event["value"])
        tolerance = max(.001, abs(value) * 1e-5)
        requests = [r for r in tx if r["type"] == "PARAM_SET" and r["system"] == 255
                    and r["fields"].get("target_system") == 1 and r["fields"].get("target_component") == 1
                    and r["fields"].get("param_id") == event["name"]
                    and abs(_finite(r["fields"]["param_value"]) - value) <= tolerance
                    and r["sim_s"] is not None and start - EPS <= r["sim_s"] <= start + 5 + EPS
                    and epoch <= r["epoch_s"] <= end_epoch]
        acknowledgments = [r for r in rx if r["type"] == "PARAM_VALUE" and r["system"] == 1 and r["component"] == 1
                           and r["fields"].get("param_id") == event["name"]
                           and abs(_finite(r["fields"]["param_value"]) - value) <= tolerance
                           and r["sim_s"] is not None and start - EPS <= r["sim_s"] <= start + 5 + EPS
                           and requests and requests[0]["epoch_s"] <= r["epoch_s"] <= end_epoch]
        evidence.append({"event_id": event["id"], "name": event["name"], "value": value,
                         "outcome": PASS if requests and acknowledgments else UNKNOWN,
                         "request_sim_s": requests[0]["sim_s"] if requests else None,
                         "ack_sim_s": acknowledgments[0]["sim_s"] if acknowledgments else None})
    passed = all(item["outcome"] == PASS for item in evidence)
    return _check("injection_transport", PASS if passed else UNKNOWN,
                  "Parameter requests and subsequent matching acknowledgments observed" if passed else "Missing matching parameter request or subsequent acknowledgment within 5 simulator seconds",
                  events=evidence, deadline_s=5)


def evaluate_run(path: Path, scenario_override: dict | None = None) -> dict:
    """Evaluate a saved run without executing simulator or runner code.

    Overrides are explicitly reported and never replace the sealed original;
    they support wrong-expectation replay against identical raw evidence.
    """
    path = Path(path)
    result = {"schema_version": 1, "scenario_id": None, "outcome": UNKNOWN,
              "scenario_override": scenario_override is not None, "checks": [], "assertions": [], "trace": {}}
    checks = result["checks"]
    try:
        run = _json(path / "run.json")
        original = _json(path / "scenario.json")
        spec = scenario_override if scenario_override is not None else original
        result["scenario_id"] = spec.get("id")
        synthetic = run.get("synthetic") is True
        result["trace"]["synthetic"] = synthetic
        integrity = _seal(path, synthetic)
        checks.append(integrity)
        if integrity["outcome"] != PASS:
            return result
        event_rows = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines() if line.strip()]
        events = {event["id"]: event for event in event_rows}
        if len(events) != len(event_rows):
            raise ValueError("Duplicate event IDs")
        baseline = events["baseline_ready"]
        end = _finite(events["scenario_end"]["sim_s"])
        baseline_time = _finite(baseline["sim_s"])
        assertions = spec.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise ValueError("Scenario has no assertions")
        assertions = [dict(a, id=a.get("id", f"assertion-{i + 1:02d}")) for i, a in enumerate(assertions)]
        identifiers = [a["id"] for a in assertions]
        if any(not isinstance(i, str) or not i for i in identifiers) or len(set(identifiers)) != len(identifiers):
            raise ValueError("Assertion IDs must be nonempty and unique")
        if spec.get("baseline") is not True and not any(a.get("fault_evidence") is True for a in assertions):
            raise ValueError("Scenario actions lack declared fault evidence assertions")
        physical_messages = {"SYS_STATUS", "BATTERY_STATUS", "RC_CHANNELS", "RC_CHANNELS_RAW", "GPS_RAW_INT", "GPS2_RAW", "EKF_STATUS_REPORT"}
        for assertion in assertions:
            if assertion.get("fault_evidence") is True:
                kind = assertion.get("type")
                if kind not in {"text", "field", "heartbeat_gap", "heartbeat_resumed"} or (kind == "field" and assertion.get("message") not in physical_messages):
                    raise ValueError("Fault evidence requires physical sensor telemetry, status text, or transmitted heartbeat evidence; mode and parameter echo do not qualify")
        for event in spec.get("events", []):
            observed = events.get(event["id"])
            if not observed or observed.get("kind") != event.get("kind"):
                raise ValueError(f"Scheduled event missing: {event['id']}")
            keys = {"heartbeat": ["enabled"], "parameter": ["name", "value"], "mode": ["mode"]}.get(event.get("kind"))
            if keys is None or any(observed.get(key) != event.get(key) for key in keys):
                raise ValueError(f"Recorded action differs from declared event: {event['id']}")
        offset = _finite(run.get("schedule_offset_s", 0))
        schedule_evidence = []
        for event in spec.get("events", []):
            expected = baseline_time + _finite(event["at_s"]) + offset
            actual = _finite(events[event["id"]]["sim_s"])
            schedule_evidence.append({"event_id": event["id"], "expected_sim_s": expected, "actual_sim_s": actual,
                                      "lateness_s": actual - expected, "valid": expected - EPS <= actual <= expected + .5 + EPS and actual <= end})
        ordered_sim = [_finite(event["sim_s"]) for event in event_rows]
        ordered_epochs = [_finite(event["host_unix_us"]) for event in event_rows]
        chronological = all(b >= a for a, b in zip(ordered_sim, ordered_sim[1:])) and all(b >= a for a, b in zip(ordered_epochs, ordered_epochs[1:]))
        schedule_ok = offset >= 0 and chronological and all(event["valid"] for event in schedule_evidence)
        checks.append(_check("event_schedule", PASS if schedule_ok else UNKNOWN,
                             "Events follow declared simulator schedule and offset" if schedule_ok else "Event chronology or declared schedule does not match recorded actions",
                             schedule_offset_s=offset, max_lateness_s=.5, events=schedule_evidence))
        compound_groups = {}
        for event in spec.get("events", []):
            compound_groups.setdefault(_finite(event["at_s"]), []).append(event["id"])
        compound_spreads = []
        for at_s, identifiers in compound_groups.items():
            if len(identifiers) > 1:
                times = [_finite(events[identifier]["sim_s"]) for identifier in identifiers]
                compound_spreads.append({"at_s": at_s, "event_ids": identifiers, "observed_skew_s": max(times) - min(times)})
        max_skew = _finite(spec.get("max_compound_skew_s", .25))
        skew_ok = max_skew >= 0 and all(group["observed_skew_s"] <= max_skew + EPS for group in compound_spreads)
        checks.append(_check("compound_timing", PASS if skew_ok else UNKNOWN, "Simultaneous event groups satisfy declared skew" if skew_ok else "Compound event timing exceeds declared maximum skew", max_skew_s=max_skew, groups=compound_spreads))
        cleanup = run.get("cleanup", {})
        clean = (run.get("error") in (None, "") and run.get("returncode") == 0
                 and isinstance(cleanup, dict) and cleanup.get("completed") is True and cleanup.get("child_reaped") is True)
        checks.append(_check("runner_cleanup", PASS if clean else UNKNOWN, "Runner completed and child reaped" if clean else "Runner exit/cleanup evidence is missing or unsuccessful", returncode=run.get("returncode"), cleanup=cleanup))
        rx, clocks, rx_errors = _read_tlog(path / "rx.tlog", True)
        tx, _, tx_errors = _read_tlog(path / "tx.tlog", False)
        checks.append(_check("raw_logs", UNKNOWN if rx_errors or tx_errors else PASS, "; ".join(rx_errors + tx_errors) or "RX and TX MAVLink logs decoded", rx_messages=len(rx), tx_messages=len(tx)))
        result["trace"].update({"rx_message_counts": dict(Counter(r["type"] for r in rx)), "tx_message_counts": dict(Counter(r["type"] for r in tx)), "clock_samples": len(clocks), "baseline_sim_s": baseline_time, "end_sim_s": end})
        if not clocks:
            checks.append(_check("simulator_clock", UNKNOWN, "No autopilot SYSTEM_TIME clock evidence"))
            return result
        epochs = [c["epoch_s"] for c in clocks]
        for row in tx:
            index = bisect_right(epochs, row["epoch_s"]) - 1
            if index >= 0:
                row["sim_s"] = clocks[index]["sim_s"]
        checks.append(_injection_transport(spec, events, rx, tx))
        clock_ok = _coverage([c["sim_s"] for c in clocks], baseline_time - 2, end)
        # A long tail with a frozen clock is not temporal coverage.
        advancing = [c for i, c in enumerate(clocks) if i == 0 or c["sim_s"] > clocks[i - 1]["sim_s"] + EPS]
        frozen_tail = clocks[-1]["epoch_s"] - advancing[-1]["epoch_s"] > MAX_SAMPLE_GAP_S
        clock_ok = clock_ok and not frozen_tail
        result["trace"].update({"first_sim_s": clocks[0]["sim_s"], "last_sim_s": clocks[-1]["sim_s"]})
        checks.append(_check("simulator_clock", PASS if clock_ok else UNKNOWN, "SYSTEM_TIME covers the observation interval" if clock_ok else "Stale, missing, or insufficient SYSTEM_TIME coverage"))
        action_errors = []
        for event in event_rows:
            sim = _finite(event["sim_s"])
            epoch = _finite(event["host_unix_us"]) / 1e6
            index = bisect_right(epochs, epoch) - 1
            if index < 0 or abs(clocks[index]["sim_s"] - sim) > MAX_SAMPLE_GAP_S:
                action_errors.append(f"Event {event['id']} is not aligned with the RX simulator clock")
        checks.append(_check("event_clock_alignment", UNKNOWN if action_errors else PASS, "; ".join(action_errors) or "Event times agree with independently decoded SYSTEM_TIME"))
        checks.append(_baseline(spec, baseline, rx))
        checks.append(_initial_state_until_event(spec, events, rx))
        required_end = baseline_time + _finite(spec["duration_s"]) + offset
        duration_ok = end + EPS >= required_end and clocks[-1]["sim_s"] + EPS >= required_end
        checks.append(_check("scenario_duration", PASS if duration_ok else UNKNOWN, "Full declared observation duration recorded" if duration_ok else "Declared observation duration is incomplete", required_end_sim_s=required_end))
        result["assertions"] = [_assertion(a, events, rx, tx, clocks, end) for a in assertions]
        # Preconditions and integrity are prerequisites for interpreting a failure.
        if any(check["outcome"] != PASS for check in checks):
            result["outcome"] = UNKNOWN
        elif any(a["outcome"] == FAIL for a in result["assertions"]):
            result["outcome"] = FAIL
        elif any(a["outcome"] != PASS for a in result["assertions"]):
            result["outcome"] = UNKNOWN
        else:
            result["outcome"] = PASS
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        checks.append(_check("evidence_read", UNKNOWN, f"Unusable evidence: {type(exc).__name__}: {exc}"))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--scenario-override", type=Path, help="Replay different expectations; raw evidence remains sealed")
    args = parser.parse_args(argv)
    try:
        override = _json(args.scenario_override) if args.scenario_override else None
        result = evaluate_run(args.run_dir, override)
    except (OSError, ValueError) as exc:
        result = {"outcome": UNKNOWN, "checks": [_check("scenario_override", UNKNOWN, str(exc))]}
    print(json.dumps(result, indent=2, allow_nan=False))
    return {PASS: 0, FAIL: 1, UNKNOWN: 2}[result["outcome"]]


if __name__ == "__main__":
    sys.exit(main())
