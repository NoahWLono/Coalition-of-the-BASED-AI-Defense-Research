"""Synthetic MAVLink fixtures; these tests do not demonstrate simulator behavior."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from pymavlink import mavutil

EPOCH = 1_700_000_000


def scenario():
    return {
        "schema_version": 1, "id": "synthetic-gcs-loss", "title": "Synthetic only",
        "preconditions": {"mode": 4, "armed": True, "min_altitude_m": 10.5, "max_altitude_m": 13.5, "max_abs_vz_cm_s": 30, "stable_for_s": 3, "min_gps_fix": 3, "min_battery_mv": 11500},
        "duration_s": 25,
        "events": [{"id": "loss", "at_s": 5, "kind": "heartbeat", "enabled": False}],
        "assertions": [
            {"id": "silence", "type": "heartbeat_gap", "after": "loss", "duration_s": 10, "fault_evidence": True},
            {"id": "land", "type": "mode", "after": "loss", "within_s": 8, "allowed": [9]},
            {"id": "failsafe", "type": "text", "after": "loss", "within_s": 8, "contains": "GCS Failsafe", "fault_evidence": True},
            {"id": "disarm", "type": "disarmed", "after": "loss", "within_s": 20},
        ],
    }


def seal(path):
    files = sorted(p for p in path.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (path / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(path).as_posix()}\n" for p in files))


def write_synthetic_run(path, *, mode_after=9, clock="normal", end=30, text=True,
                        resume=False, initial_mode=4, cleanup=True, armed_initial=True,
                        no_heartbeats=False, altitude=12000, gps_fix=3,
                        tx_during_gap=False, source_system=1, source_component=1, last_pre_event_same_tick=False, sample_step_s=.2, vz=0, initial_battery_mv=12000, fault_battery_mv=10500, parameter_event=False, parameter_tx=True, parameter_ack=True, sparse_battery_after_fault=False, early_land_before_fault=False, status_text=b"GCS Failsafe"):
    """Hand-built independent tlog producer, without importing production helpers."""
    path.mkdir(parents=True, exist_ok=True)
    spec = scenario()
    events = [
        {"id": "baseline_ready", "kind": "baseline_ready", "sim_s": 5, "host_monotonic_ns": 1, "host_unix_us": int((EPOCH + 1.25) * 1e6)},
        {"id": "loss", "kind": "heartbeat", "enabled": False, "sim_s": 10, "host_monotonic_ns": 2, "host_unix_us": int((EPOCH + 2.5) * 1e6)},
        {"id": "scenario_end", "kind": "scenario_end", "sim_s": end, "host_monotonic_ns": 3, "host_unix_us": int((EPOCH + end / 4 + .1) * 1e6)},
    ]
    if parameter_event:
        spec["events"][0] = {"id": "loss", "at_s": 5, "kind": "parameter", "name": "SIM_BATT_VOLTAGE", "value": 10.5}
        events[1].update(kind="parameter", name="SIM_BATT_VOLTAGE", value=10.5)
        spec["assertions"] = [
            {"id": "voltage-low", "type": "field", "after": "loss", "within_s": 8, "message": "SYS_STATUS", "field": "voltage_battery", "op": "lt", "value": 11000, "fault_evidence": True},
            spec["assertions"][1], spec["assertions"][3],
        ]
    if last_pre_event_same_tick:
        events[1]["host_unix_us"] += 100
    if resume:
        spec["events"].append({"id": "recovery", "at_s": 15, "kind": "heartbeat", "enabled": True})
        events.insert(2, {"id": "recovery", "kind": "heartbeat", "enabled": True, "sim_s": 20, "host_monotonic_ns": 3, "host_unix_us": int((EPOCH + 5) * 1e6)})
        spec["assertions"].extend([
            {"id": "resumed", "type": "heartbeat_resumed", "after": "recovery", "within_s": 2, "fault_evidence": True},
            {"id": "recovery-hold", "type": "hold_mode", "after": "recovery", "start_s": 0, "duration_s": 5, "allowed": [9]},
        ])
    (path / "scenario.json").write_text(json.dumps(spec))
    (path / "events.jsonl").write_text("".join(json.dumps(x) + "\n" for x in events))
    (path / "run.json").write_text(json.dumps({"synthetic": True, "returncode": 0, "error": None, "cleanup": {"completed": cleanup, "child_reaped": cleanup}}))
    rx = mavutil.mavlink.MAVLink(None, srcSystem=source_system, srcComponent=source_component)
    with (path / "rx.tlog").open("wb") as file:
        def emit(message, t, offset=0):
            file.write(struct.pack(">Q", int((EPOCH + t / 4 + offset) * 1e6)))
            file.write(message.pack(rx))
            rx.seq = (rx.seq + 1) % 256
        for step in range(round(end / sample_step_s) + 1):
            t = round(step * sample_step_s, 6)
            if clock != "missing":
                boot = min(t, 11) if clock == "stale" else t
                emit(rx.system_time_encode(int((EPOCH + t) * 1e6), int(boot * 1000)), t)
            if parameter_event and parameter_ack and t == 10:
                emit(rx.param_value_encode(b"SIM_BATT_VOLTAGE", 10.5, 9, 1, 0), t, .00002)
            if not no_heartbeats:
                mode = initial_mode if t < 14 else mode_after
                if early_land_before_fault and 7 <= t < 10:
                    mode = 9
                emit(rx.heartbeat_encode(2, 3, 128 if t < 26 and armed_initial else 0, mode, 4), t, .0001)
            emit(rx.global_position_int_encode(int(t * 1000), 100000, 100000, altitude, altitude, 0, 0, vz, 0), t, .0002)
            emit(rx.gps_raw_int_encode(int(t * 1000000), gps_fix, 100000, 100000, altitude, 100, 100, 0, 0, 12), t, .0003)
            if not sparse_battery_after_fault or t <= 10:
                emit(rx.sys_status_encode(0, 0, 0, 0, initial_battery_mv if t < 10 else fault_battery_mv, 0, 70, 0, 0, 0, 0, 0, 0), t, .0004)
            if t == 14 and text:
                emit(rx.statustext_encode(4, status_text), t, .0005)
    tx = mavutil.mavlink.MAVLink(None, srcSystem=255, srcComponent=190)
    with (path / "tx.tlog").open("wb") as file:
        for step in range(round(end / sample_step_s) + 1):
            t = round(step * sample_step_s, 6)
            if parameter_event and parameter_tx and t == 10:
                file.write(struct.pack(">Q", int((EPOCH + t / 4 + .00001) * 1e6)))
                file.write(tx.param_set_encode(1, 1, b"SIM_BATT_VOLTAGE", 10.5, 9).pack(tx))
                tx.seq = (tx.seq + 1) % 256
            if t < 10 or (resume and t >= 20) or (tx_during_gap and t == 15) or (last_pre_event_same_tick and t == 10):
                file.write(struct.pack(">Q", int((EPOCH + t / 4 + .00005) * 1e6)))
                file.write(tx.heartbeat_encode(6, 8, 0, 0, 4).pack(tx))
                tx.seq = (tx.seq + 1) % 256
    seal(path)
    return spec


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-failsafe-")
        self.path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def evaluate(self, override=None):
        self.assertIsNotNone(importlib.util.find_spec("failsafelab.evaluate"), "independent evaluator must exist")
        from failsafelab.evaluate import evaluate_run
        return evaluate_run(self.path, scenario_override=override)

    def test_complete_transition_passes_with_fault_evidence(self):
        write_synthetic_run(self.path)
        result = self.evaluate()
        self.assertEqual(result["outcome"], "PASS", result)
        self.assertEqual(len(result["assertions"]), 4)
        self.assertTrue(result["trace"]["synthetic"])

    def test_wrong_allowed_mode_fails_without_changing_raw_trace(self):
        spec = write_synthetic_run(self.path)
        spec["assertions"][1]["allowed"] = [6]
        self.assertEqual(self.evaluate(spec)["outcome"], "FAIL")

    def test_disabled_failsafe_still_guided_is_observed_failure(self):
        write_synthetic_run(self.path, mode_after=4)
        self.assertEqual(self.evaluate()["outcome"], "FAIL")

    def test_missing_fault_message_cannot_pass(self):
        write_synthetic_run(self.path, text=False)
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_stale_and_missing_clocks_are_indeterminate(self):
        for clock in ["stale", "missing"]:
            with self.subTest(clock=clock):
                write_synthetic_run(self.path, clock=clock)
                self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_incomplete_window_coverage_is_indeterminate(self):
        write_synthetic_run(self.path, end=17)
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_recovery_requires_continued_land_and_heartbeat_return(self):
        write_synthetic_run(self.path, resume=True)
        self.assertEqual(self.evaluate()["outcome"], "PASS")
        spec = json.loads((self.path / "scenario.json").read_text())
        spec["assertions"][-1]["allowed"] = [4]
        self.assertEqual(self.evaluate(spec)["outcome"], "FAIL")

    def test_checksum_tampering_is_indeterminate(self):
        write_synthetic_run(self.path)
        with (self.path / "rx.tlog").open("ab") as file:
            file.write(b"tampered")
        result = self.evaluate()
        self.assertEqual(result["outcome"], "INDETERMINATE")
        self.assertIn("checksum", json.dumps(result).lower())

    def test_missing_seal_cannot_pass_actual_run(self):
        write_synthetic_run(self.path)
        run = json.loads((self.path / "run.json").read_text())
        run.pop("synthetic")
        (self.path / "run.json").write_text(json.dumps(run))
        (self.path / "SHA256SUMS").unlink()
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_cleanup_failure_cannot_pass(self):
        write_synthetic_run(self.path, cleanup=False)
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_baseline_must_be_observed_not_only_claimed(self):
        for kw in [{"initial_mode": 9}, {"armed_initial": False}, {"altitude": 2000}, {"gps_fix": 1}]:
            with self.subTest(kw=kw):
                write_synthetic_run(self.path, **kw)
                self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_missing_autopilot_heartbeats_cannot_pass(self):
        write_synthetic_run(self.path, no_heartbeats=True)
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_other_system_or_component_heartbeats_do_not_count(self):
        for kw in [{"source_system": 42}, {"source_component": 99}]:
            with self.subTest(kw=kw):
                write_synthetic_run(self.path, **kw)
                self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_transmitted_heartbeat_inside_gap_fails(self):
        write_synthetic_run(self.path, tx_during_gap=True)
        self.assertEqual(self.evaluate()["outcome"], "FAIL")

    def test_field_comparison_reads_mavlink_value(self):
        spec = write_synthetic_run(self.path)
        spec["assertions"].append({"id": "voltage", "type": "field", "after": "loss", "message": "SYS_STATUS", "field": "voltage_battery", "op": "lt", "value": 11000, "within_s": 5, "fault_evidence": True})
        self.assertEqual(self.evaluate(spec)["outcome"], "PASS")
        spec["assertions"][-1]["value"] = 10000
        self.assertEqual(self.evaluate(spec)["outcome"], "FAIL")

    def test_empty_assertions_and_no_fault_evidence_cannot_pass(self):
        for assertions in [[], [{"id": "land", "type": "mode", "after": "loss", "within_s": 8, "allowed": [9]}]]:
            with self.subTest(assertions=assertions):
                spec = write_synthetic_run(self.path)
                spec["assertions"] = assertions
                self.assertEqual(self.evaluate(spec)["outcome"], "INDETERMINATE")

    def test_missing_or_empty_raw_logs_are_indeterminate(self):
        for target in ["rx.tlog", "tx.tlog"]:
            with self.subTest(target=target):
                write_synthetic_run(self.path)
                (self.path / target).write_bytes(b"")
                seal(self.path)
                self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_assertion_ids_are_optional_in_contract(self):
        spec = write_synthetic_run(self.path)
        for assertion in spec["assertions"]:
            assertion.pop("id")
        self.assertEqual(self.evaluate(spec)["outcome"], "PASS")

    def test_declared_baseline_allows_commanded_landing_without_fault(self):
        spec = write_synthetic_run(self.path)
        spec["baseline"] = True
        spec["events"] = [{"id": "loss", "at_s": 5, "kind": "mode", "mode": "LAND"}]
        spec["assertions"] = [spec["assertions"][1], spec["assertions"][3]]
        events = [json.loads(line) for line in (self.path / "events.jsonl").read_text().splitlines()]
        events[1].update(kind="mode", mode="LAND")
        (self.path / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        seal(self.path)
        self.assertEqual(self.evaluate(spec)["outcome"], "PASS")

    def test_pre_stop_heartbeat_in_same_sim_tick_is_not_gap_violation(self):
        write_synthetic_run(self.path, last_pre_event_same_tick=True)
        self.assertEqual(self.evaluate()["outcome"], "PASS")

    def test_mode_is_not_physical_fault_evidence(self):
        spec = write_synthetic_run(self.path)
        spec["assertions"] = [spec["assertions"][1]]
        spec["assertions"][0]["fault_evidence"] = True
        self.assertEqual(self.evaluate(spec)["outcome"], "INDETERMINATE")

    def test_events_cannot_claim_different_action_from_scenario(self):
        write_synthetic_run(self.path)
        events = [json.loads(line) for line in (self.path / "events.jsonl").read_text().splitlines()]
        events[1]["enabled"] = True
        (self.path / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        seal(self.path)
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_baseline_requires_stable_fresh_sensor_streams(self):
        for kw in [{"altitude": 16000}, {"vz": 31}, {"initial_battery_mv": 11500}, {"gps_fix": 255}, {"sample_step_s": 1}]:
            with self.subTest(kw=kw):
                write_synthetic_run(self.path, **kw)
                self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_compound_events_cannot_exceed_declared_skew(self):
        spec = write_synthetic_run(self.path)
        spec["max_compound_skew_s"] = .25
        spec["events"].append({"id": "second", "at_s": 5, "kind": "heartbeat", "enabled": False})
        events = [json.loads(line) for line in (self.path / "events.jsonl").read_text().splitlines()]
        events.insert(2, {"id": "second", "kind": "heartbeat", "enabled": False, "sim_s": 10.8, "host_monotonic_ns": 3, "host_unix_us": int((EPOCH + 2.7) * 1e6)})
        (self.path / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        seal(self.path)
        self.assertEqual(self.evaluate(spec)["outcome"], "INDETERMINATE")

    def test_after_end_packet_cannot_supply_disarm_evidence(self):
        spec = write_synthetic_run(self.path, end=26)
        spec["duration_s"] = 21
        spec["assertions"][-1]["within_s"] = 16
        events = [json.loads(line) for line in (self.path / "events.jsonl").read_text().splitlines()]
        events[-1]["host_unix_us"] = int((EPOCH + 26 / 4) * 1e6)
        (self.path / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        seal(self.path)
        self.assertEqual(self.evaluate(spec)["outcome"], "FAIL")

    def test_unknown_battery_sentinel_is_not_recovery(self):
        spec = write_synthetic_run(self.path, fault_battery_mv=65535)
        spec["assertions"].append({"type": "field", "after": "loss", "within_s": 5, "message": "SYS_STATUS", "field": "voltage_battery", "op": "gt", "value": 11500, "fault_evidence": True})
        self.assertEqual(self.evaluate(spec)["outcome"], "INDETERMINATE")

    def test_parameter_injection_requires_matching_tx_and_ack(self):
        write_synthetic_run(self.path, parameter_event=True)
        self.assertEqual(self.evaluate()["outcome"], "PASS")
        for kw in [{"parameter_tx": False}, {"parameter_ack": False}]:
            with self.subTest(kw=kw):
                write_synthetic_run(self.path, parameter_event=True, **kw)
                self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_event_must_match_declared_schedule_and_offset(self):
        write_synthetic_run(self.path)
        run = json.loads((self.path / "run.json").read_text())
        run["schedule_offset_s"] = 1.4
        (self.path / "run.json").write_text(json.dumps(run))
        seal(self.path)
        self.assertEqual(self.evaluate()["outcome"], "INDETERMINATE")

    def test_sparse_nonmatching_field_is_indeterminate_not_failure(self):
        write_synthetic_run(self.path, parameter_event=True, sparse_battery_after_fault=True, fault_battery_mv=12000)
        result = self.evaluate()
        self.assertTrue(all(check["outcome"] == "PASS" for check in result["checks"]), result)
        self.assertEqual(result["assertions"][0]["observations"], [{"sim_s": 10.0, "value": 12000.0}])
        self.assertEqual(result["assertions"][0]["outcome"], "INDETERMINATE")
        self.assertEqual(result["outcome"], "INDETERMINATE")

    def test_sparse_matching_field_still_proves_existential_assertion(self):
        write_synthetic_run(self.path, parameter_event=True, sparse_battery_after_fault=True, fault_battery_mv=10500)
        result = self.evaluate()
        self.assertEqual(result["assertions"][0]["observations"], [{"sim_s": 10.0, "value": 10500.0}])
        self.assertEqual(result["assertions"][0]["outcome"], "PASS")
        self.assertEqual(result["outcome"], "PASS")

    def test_initial_mode_must_continue_until_first_event(self):
        write_synthetic_run(self.path, early_land_before_fault=True)
        result = self.evaluate()
        self.assertEqual(next(check for check in result["checks"] if check["id"] == "baseline")["outcome"], "PASS")
        self.assertTrue(all(assertion["outcome"] == "PASS" for assertion in result["assertions"]), result)
        self.assertEqual(result["outcome"], "INDETERMINATE")

    def test_text_alternatives_accept_only_declared_gcs_branches(self):
        cases = [
            ({"status_text": b"GCS Failsafe"}, "PASS"),
            ({"status_text": b"GCS + Battery Failsafe - Continuing Landing"}, "PASS"),
            ({"status_text": b"Battery Failsafe - Continuing Landing"}, "FAIL"),
            ({"text": False}, "INDETERMINATE"),
        ]
        for options, outcome in cases:
            with self.subTest(options=options):
                spec = write_synthetic_run(self.path, **options)
                spec["assertions"][2].pop("contains")
                spec["assertions"][2]["contains_any"] = ["GCS Failsafe", "GCS + Battery Failsafe"]
                result = self.evaluate(spec)
                self.assertEqual(result["assertions"][2]["outcome"], outcome)
                self.assertEqual(result["outcome"], outcome)

    def test_text_alternatives_reject_empty_malformed_or_ambiguous_lists(self):
        for alternatives in [[], [""], [" "], ["GCS Failsafe", 4], "GCS Failsafe"]:
            with self.subTest(alternatives=alternatives):
                spec = write_synthetic_run(self.path)
                spec["assertions"][2].pop("contains")
                spec["assertions"][2]["contains_any"] = alternatives
                self.assertEqual(self.evaluate(spec)["outcome"], "INDETERMINATE")
        spec = write_synthetic_run(self.path)
        spec["assertions"][2]["contains_any"] = ["GCS Failsafe"]
        self.assertEqual(self.evaluate(spec)["outcome"], "INDETERMINATE")

    def test_cli_outputs_json_and_outcome_exit_code(self):
        for kw, code, outcome in [({}, 0, "PASS"), ({"mode_after": 4}, 1, "FAIL"), ({"clock": "missing"}, 2, "INDETERMINATE")]:
            with self.subTest(outcome=outcome):
                write_synthetic_run(self.path, **kw)
                proc = subprocess.run([sys.executable, "-m", "failsafelab.evaluate", str(self.path)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, code, proc.stderr + proc.stdout)
                self.assertEqual(json.loads(proc.stdout)["outcome"], outcome)
                self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
