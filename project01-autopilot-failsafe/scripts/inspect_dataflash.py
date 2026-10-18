#!/usr/bin/env python3
"""Read onboard DataFlash records independently of the lab runner and evaluator.

Usage: .venv/bin/python scripts/inspect_dataflash.py RUN_DIR [RUN_DIR ...]
       Add --output evidence/trace-inspection.json to retain the result.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

from pymavlink.DFReader import DFReader_binary
from pymavlink import mavutil


REASONS = {1: "RC_COMMAND", 2: "GCS_COMMAND", 3: "RADIO_FAILSAFE",
           4: "BATTERY_FAILSAFE", 5: "GCS_FAILSAFE", 6: "EKF_FAILSAFE",
           26: "INITIALISED", 50: "DEADRECKON_FAILSAFE"}
SUBSYSTEMS = {2: "RADIO", 3: "COMPASS", 5: "FAILSAFE_RADIO",
              6: "FAILSAFE_BATT", 8: "FAILSAFE_GCS", 11: "GPS",
              16: "EKFCHECK", 17: "FAILSAFE_EKFINAV", 31: "FAILSAFE_DEADRECKON"}
SELECT = {"MODE", "ERR", "BAT", "GPS", "MSG", "ARM", "PARM", "DSF", "RCI2"}


def json_safe(value):
    """Keep non-finite raw values explicit while producing strict JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def changes(rows: list[dict], key: str) -> list[dict]:
    result = []
    for row in rows:
        if not result or result[-1][key] != row[key]:
            result.append(row)
    return result


def mode_at(modes: list[dict], when: float) -> int | None:
    prior = [r for r in modes if r["sim_s"] <= when]
    return prior[-1]["Mode"] if prior else None


def read_dataflash(paths: list[Path]) -> dict:
    rows = {name: [] for name in SELECT}
    counts = Counter()
    maximum = 0.0
    formats = {}
    for path in paths:
        reader = DFReader_binary(str(path))
        while (message := reader.recv_msg()) is not None:
            kind = message.get_type()
            counts[kind] += 1
            if hasattr(message, "TimeUS"):
                maximum = max(maximum, message.TimeUS / 1e6)
            if kind not in SELECT:
                continue
            record = message.to_dict()
            record.pop("mavpackettype", None)
            if "TimeUS" not in record:
                raise ValueError(f"Missing TimeUS in {kind} in {path}")
            record["sim_s"] = record["TimeUS"] / 1e6
            formats.setdefault(kind, list(message._fieldnames))
            if kind == "PARM" and record["Name"] not in {
                    "SIM_RC_FAIL", "SIM_BATT_VOLTAGE", "SIM_GPS_BYTELOSS"}:
                continue
            rows[kind].append(record)
        reader.close()
    for records in rows.values():
        records.sort(key=lambda row: row["sim_s"])
    for record in rows["MODE"]:
        record["reason_name"] = REASONS.get(record["Rsn"], "OTHER")
    for record in rows["ERR"]:
        record["subsystem_name"] = SUBSYSTEMS.get(record["Subsys"], "OTHER")
        if record["Subsys"] in {5, 6, 8, 17, 31}:
            record["meaning"] = {0: "RESOLVED", 1: "OCCURRED"}.get(record["ECode"], "OTHER")
    return {"rows": rows, "counts": dict(counts), "last_sim_s": maximum,
            "field_definitions_from_log": formats}


def read_mavlink(path: Path) -> dict:
    reader = mavutil.mavlink_connection(str(path), robust_parsing=False)
    clock = None
    modes, clocks, texts = [], [], []
    while (message := reader.recv_match()) is not None:
        if message.get_srcSystem() != 1 or message.get_srcComponent() != 1:
            continue
        kind = message.get_type()
        if kind == "SYSTEM_TIME":
            clock = message.time_boot_ms / 1000
            clocks.append(clock)
        elif kind == "HEARTBEAT" and clock is not None:
            modes.append({"sim_s": clock, "Mode": message.custom_mode,
                          "armed": bool(message.base_mode & 128)})
        elif kind == "STATUSTEXT" and clock is not None:
            if any(word in message.text.lower() for word in ("failsafe", "variance", "dead reckoning", "battery 1 is")):
                texts.append({"sim_s": clock, "text": message.text})
    reader.close()
    return {"modes": changes(modes, "Mode"), "statuses": texts,
            "system_time_samples": len(clocks),
            "max_system_time_gap_s": max((b-a for a, b in zip(clocks, clocks[1:])), default=None),
            "last_sim_s": clocks[-1] if clocks else None}


def inspect(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    logs = sorted((run_dir / "logs").glob("*.BIN"))
    if not logs:
        raise ValueError(f"No DataFlash BIN logs in {run_dir}")
    seal = {}
    for line in (run_dir / "SHA256SUMS").read_text().splitlines():
        sha, relative = line.split("  ", 1)
        seal[relative] = sha
    inputs = logs + [run_dir / name for name in
                     ("rx.tlog", "events.jsonl", "scenario.json", "run.json")]
    hashes = {str(p.relative_to(run_dir)): digest(p) for p in inputs}
    if any(seal.get(name) != sha for name, sha in hashes.items()):
        raise ValueError(f"Input evidence differs from SHA256SUMS in {run_dir}")
    scenario = json.loads((run_dir / "scenario.json").read_text())
    run = json.loads((run_dir / "run.json").read_text())
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    baseline = next(e["sim_s"] for e in events if e["id"] == "baseline_ready")
    end = next(e["sim_s"] for e in events if e["id"] == "scenario_end")
    df = read_dataflash(logs)
    rows = df.pop("rows")
    df_modes = changes(rows["MODE"], "Mode")
    mav = read_mavlink(run_dir / "rx.tlog")
    matching = [r["Mode"] for r in df_modes] == [r["Mode"] for r in mav["modes"]]
    crosschecks = [
        {"name": "sealed_inputs_match", "passed": True},
        {"name": "dataflash_covers_observation", "passed": df["last_sim_s"] >= end},
        {"name": "mode_sequence_matches_mavlink", "passed": matching},
    ]
    comparison = []
    if matching:
        for onboard, telemetry in zip(df_modes, mav["modes"]):
            comparison.append({"Mode": onboard["Mode"], "dataflash_s": onboard["sim_s"],
                               "mavlink_assigned_s": telemetry["sim_s"],
                               "mavlink_minus_dataflash_s": telemetry["sim_s"] - onboard["sim_s"]})
    battery = [r for r in rows["BAT"] if r["Inst"] == 0 and baseline <= r["sim_s"] <= end]
    gps = [r for r in rows["GPS"] if r["I"] == 0]
    df.update({"mode_records": rows["MODE"], "modes": df_modes, "errors": rows["ERR"],
               "arm_records": rows["ARM"], "fault_parameter_records": rows["PARM"],
               "messages": [r for r in rows["MSG"] if any(w in r["Message"].lower()
                             for w in ("failsafe", "variance", "dead reckoning", "battery 1 is"))],
               "battery": {"samples": len(battery), "min_volt": min((r["Volt"] for r in battery), default=None),
                           "max_volt": max((r["Volt"] for r in battery), default=None)},
               "gps": {"samples": len(gps), "status_transitions": changes(gps, "Status")},
               "logger_dropped_max": max((r["Dp"] for r in rows["DSF"]), default=None)})
    fault_errors = [r for r in rows["ERR"] if baseline <= r["sim_s"] <= end]
    pre_drops = [r["Dp"] for r in rows["DSF"] if r["sim_s"] <= baseline]
    observation_drops = [r["Dp"] for r in rows["DSF"] if baseline <= r["sim_s"] <= end]
    dropped_during = max(observation_drops) - pre_drops[-1] if pre_drops and observation_drops else None
    df["logger_drop_counter_changes"] = changes(rows["DSF"], "Dp")
    df["logger_dropped_during_observation"] = dropped_during
    crosschecks.append({"name": "logger_reports_no_new_drops_during_observation",
                        "passed": dropped_during == 0,
                        "startup_dropped": pre_drops[-1] if pre_drops else None,
                        "observation_dropped": dropped_during})
    restoration = next((e for e in events if e["id"] == "restore"), None)
    if restoration and scenario["id"] in {"04-gcs-recovery", "05-rc-recovery"}:
        subsystem = 8 if scenario["id"].startswith("04") else 5
        clear = [r for r in fault_errors if r["Subsys"] == subsystem and r["ECode"] == 0
                 and r["sim_s"] >= restoration["sim_s"]]
        still_land = mode_at(df_modes, restoration["sim_s"]) == 9 and not any(
            r["Mode"] != 9 for r in df_modes if restoration["sim_s"] < r["sim_s"] <= end)
        df["recovery_interval"] = {"restoration_event_s": restoration["sim_s"],
                                   "first_clear_record": clear[0] if clear else None,
                                   "through_s": end, "LAND_persists": still_land}
        crosschecks.append({"name": "recovery_clears_detector_and_retains_land", "passed": bool(clear) and still_land})
    stale = next((e for e in events if e.get("name") == "SIM_GPS_BYTELOSS" and e.get("value") == 100), None)
    if stale:
        valid = [r for r in gps if r["Status"] >= 3 and r["sim_s"] <= stale["sim_s"]]
        absent = [r for r in gps if r["Status"] < 3 and r["sim_s"] >= stale["sim_s"]]
        df["gps_starvation"] = {"event_s": stale["sim_s"], "last_valid_before": valid[-1] if valid else None,
                                "first_invalid_after": absent[0] if absent else None,
                                "invalid_after_event_s": absent[0]["sim_s"] - stale["sim_s"] if absent else None}
        crosschecks.append({"name": "gps_loss_visible_in_onboard_records", "passed": bool(valid and absent)})
    if scenario["id"] == "10-gcs-rc-compound":
        seen = {r["Subsys"] for r in fault_errors if r["ECode"] == 1}
        crosschecks.append({"name": "both_gcs_and_radio_detectors_logged", "passed": {5, 8}.issubset(seen),
                            "occurred_subsystems": sorted(seen)})
    return {"run_dir": str(run_dir), "scenario_id": scenario["id"], "version": run["version"],
            "baseline_s": baseline, "scenario_end_s": end, "input_sha256": hashes,
            "events": events, "dataflash": df, "mavlink": mav,
            "mode_time_comparison": comparison, "crosschecks": crosschecks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {"schema_version": 1, "method": "Direct pymavlink DFReader_binary plus separate MAVLink decode; no runner/evaluator imports",
              "inspector_sha256": digest(Path(__file__)),
              "pymavlink_version": importlib.metadata.version("pymavlink"),
              "annotation_producer": "Assistant-authored deterministic reader; assistant direct trace inspection recorded separately",
              "nonfinite_encoding": "Non-finite raw floats are preserved as NaN, Infinity, or -Infinity strings",
              "qualified_human_review": False, "runs": [inspect(p) for p in args.runs]}
    content = json.dumps(json_safe(report), indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(content)
    else:
        print(content, end="")
    return 0 if all(check["passed"] for run in report["runs"] for check in run["crosschecks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
