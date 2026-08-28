"""Tests for revolver.diagnosis — sentry report parsing, raw-artifact fallback,
round-trip, validation, and the house exit-code convention."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from revolver.diagnosis import (
    Diagnosis,
    diagnose,
    parse_raw_artifacts,
    parse_sentry_report,
)


# ---------------------------------------------------------------------------
# parse_sentry_report
# ---------------------------------------------------------------------------


class TestParseSentryReport:
    def test_healthy(self):
        text = (
            "driver: alive\n"
            "driver-death: none\n"
            "wall-kill-no-merge: none\n"
            "stall: none (no stall detected)\n"
            "live work: no\n"
            "cycles: started=[1, 2, 3] done=[1, 2, 3] in_flight=[] wall_kill=[]\n"
            "gate-blocks: []\n"
            "verdict: HEALTHY\n"
        )
        d = parse_sentry_report(text)
        assert d.driver_alive is True
        assert d.driver_death_cycle is None
        assert d.wall_kill_cycle is None
        assert d.stall_action == "none"
        assert d.live_work is False
        assert d.cycles_started == [1, 2, 3]
        assert d.cycles_done == [1, 2, 3]
        assert d.cycles_in_flight == []
        assert d.cycles_wall_kill == []
        assert d.gate_blocks == []
        assert d.verdict == "HEALTHY"
        assert d.failure_mode == "none"
        assert d.action_needed is False
        assert d.exit_code == 0
        assert d.source == "sentry-report"

    def test_driver_death(self):
        text = (
            "driver: dead\n"
            "driver-death: DETECTED cycle 8\n"
            "wall-kill-no-merge: none\n"
            "stall: none (no stall detected)\n"
            "live work: no\n"
            "cycles: started=[1, 2, 3, 8] done=[1, 2, 3] in_flight=[8] wall_kill=[]\n"
            "gate-blocks: []\n"
            "verdict: ACTION NEEDED\n"
        )
        d = parse_sentry_report(text)
        assert d.driver_alive is False
        assert d.driver_death_cycle == 8
        assert d.failure_mode == "driver-death"
        assert d.action_needed is True
        assert d.exit_code == 1

    def test_wall_kill(self):
        text = (
            "driver: alive\n"
            "driver-death: none\n"
            "wall-kill-no-merge: DETECTED cycle 11\n"
            "stall: none (no stall detected)\n"
            "live work: no\n"
            "cycles: started=[1, 11] done=[1] in_flight=[11] wall_kill=[11]\n"
            "gate-blocks: []\n"
            "verdict: ACTION NEEDED\n"
        )
        d = parse_sentry_report(text)
        assert d.wall_kill_cycle == 11
        assert d.cycles_wall_kill == [11]
        assert d.failure_mode == "wall-kill"
        assert d.action_needed is True

    def test_stall_kill(self):
        text = (
            "driver: alive\n"
            "driver-death: none\n"
            "wall-kill-no-merge: none\n"
            "stall: kill (stalled, socket dead, inner pid 12345)\n"
            "live work: no\n"
            "cycles: started=[5] done=[] in_flight=[5] wall_kill=[]\n"
            "gate-blocks: []\n"
            "verdict: ACTION NEEDED\n"
        )
        d = parse_sentry_report(text)
        assert d.stall_action == "kill"
        assert "12345" in d.stall_reason
        assert d.failure_mode == "stall-kill"
        assert d.action_needed is True

    def test_live_work(self):
        text = (
            "driver: alive\n"
            "driver-death: none\n"
            "wall-kill-no-merge: none\n"
            "stall: wait (live work in process tree)\n"
            "live work: yes (root=9999) :: python3 run.py | curl http://...\n"
            "cycles: started=[3] done=[] in_flight=[3] wall_kill=[]\n"
            "gate-blocks: []\n"
            "verdict: HEALTHY\n"
        )
        d = parse_sentry_report(text)
        assert d.live_work is True
        assert d.live_work_root == 9999
        assert d.stall_action == "wait"
        assert d.action_needed is False  # wait is not action-needed

    def test_gate_blocks(self):
        text = (
            "driver: alive\n"
            "driver-death: none\n"
            "wall-kill-no-merge: none\n"
            "stall: none (no stall detected)\n"
            "live work: no\n"
            "cycles: started=[1, 2, 3] done=[1] in_flight=[2, 3] wall_kill=[]\n"
            "gate-blocks: [2, 3]\n"
            "verdict: HEALTHY\n"
        )
        d = parse_sentry_report(text)
        assert d.gate_blocks == [2, 3]

    def test_empty_text(self):
        d = parse_sentry_report("")
        assert d.driver_alive is True  # default
        assert d.verdict == "HEALTHY"
        assert d.action_needed is False

    def test_to_dict(self):
        text = "driver: alive\nverdict: HEALTHY\n"
        d = parse_sentry_report(text)
        dd = d.to_dict()
        assert dd["driver_alive"] is True
        assert dd["verdict"] == "HEALTHY"
        assert dd["source"] == "sentry-report"


# ---------------------------------------------------------------------------
# parse_raw_artifacts
# ---------------------------------------------------------------------------


class TestParseRawArtifacts:
    def test_cycles_out_markers(self):
        cycles = (
            "========== CYCLE 1  2025-01-01 10:00:00Z ==========\n"
            "some output\n"
            "========== CYCLE 1 done ==========\n"
            "========== CYCLE 2  2025-01-01 11:00:00Z ==========\n"
            "more output\n"
        )
        d = parse_raw_artifacts(cycles_out_text=cycles)
        assert d.cycles_started == [1, 2]
        assert d.cycles_done == [1]
        assert d.cycles_in_flight == [2]
        assert d.verdict == "ACTION NEEDED"
        assert d.source == "raw-artifacts"

    def test_all_done(self):
        cycles = (
            "========== CYCLE 1  2025-01-01 10:00:00Z ==========\n"
            "========== CYCLE 1 done ==========\n"
            "========== CYCLE 2  2025-01-01 11:00:00Z ==========\n"
            "========== CYCLE 2 done ==========\n"
        )
        d = parse_raw_artifacts(cycles_out_text=cycles)
        assert d.cycles_started == [1, 2]
        assert d.cycles_done == [1, 2]
        assert d.cycles_in_flight == []
        assert d.verdict == "HEALTHY"

    def test_empty(self):
        d = parse_raw_artifacts()
        assert d.cycles_started == []
        assert d.verdict == "HEALTHY"
        assert d.source == "raw-artifacts"

    def test_trajectory_outcome(self):
        d = parse_raw_artifacts(trajectory_outcome="max_steps_reached")
        assert "max_steps_reached" in d.evidence

    def test_gate_log_headings(self):
        gate = "## Cycle 1 — Done\n## Cycle 2 — IN PROGRESS\n"
        d = parse_raw_artifacts(gate_log_text=gate)
        assert d.gate_blocks == [1, 2]


# ---------------------------------------------------------------------------
# Diagnosis round-trip + validation + exit-code
# ---------------------------------------------------------------------------


class TestDiagnosisRecord:
    def test_round_trip(self):
        d = Diagnosis(
            pipeline_id="revolver",
            failure_mode="driver-death",
            evidence="cycle 8 died",
            endpoint_pin="http://192.168.1.157:8080/v1",
            driver_alive=False,
            driver_death_cycle=8,
            cycles_started=[1, 2, 8],
            cycles_done=[1, 2],
            cycles_in_flight=[8],
            verdict="ACTION NEEDED",
            source="sentry-report",
            raw="raw text",
        )
        dd = d.to_dict()
        d2 = Diagnosis.from_dict(dd)
        assert d2 == d
        assert d2.to_dict() == dd

    def test_round_trip_defaults(self):
        d = Diagnosis()
        assert Diagnosis.from_dict(d.to_dict()) == d

    def test_validate_accepts_valid(self):
        d = Diagnosis(source="raw-artifacts", verdict="HEALTHY", stall_action="wait")
        assert d.validate() is d

    def test_validate_rejects_bad_source(self):
        d = Diagnosis(source="bogus")
        with pytest.raises(ValueError, match="unknown source"):
            d.validate()

    def test_validate_rejects_bad_verdict(self):
        d = Diagnosis(verdict="MAYBE")
        with pytest.raises(ValueError, match="unknown verdict"):
            d.validate()

    def test_validate_rejects_bad_stall_action(self):
        d = Diagnosis(stall_action="explode")
        with pytest.raises(ValueError, match="unknown stall_action"):
            d.validate()

    def test_exit_code_healthy(self):
        assert Diagnosis().exit_code == 0

    def test_exit_code_action(self):
        assert Diagnosis(driver_death_cycle=8).exit_code == 1
        assert Diagnosis(wall_kill_cycle=11).exit_code == 1
        assert Diagnosis(stall_action="kill").exit_code == 1


# ---------------------------------------------------------------------------
# diagnose (high-level, with I/O seam)
# ---------------------------------------------------------------------------


class TestDiagnose:
    def test_with_seam(self, tmp_path: Path):
        (tmp_path / "cycles.out").write_text(
            "========== CYCLE 1  2025-01-01 ==========\n"
            "========== CYCLE 1 done ==========\n"
        )
        ai_dir = tmp_path / "ai"
        ai_dir.mkdir()
        (ai_dir / "cycle-001-revolver-gate.md").write_text("## Cycle 1 — Done\n")

        d = diagnose(tmp_path, sentry_available=False)
        assert d.source == "raw-artifacts"
        assert d.cycles_done == [1]
        assert d.verdict == "HEALTHY"

    def test_with_trajectory(self, tmp_path: Path):
        ai_dir = tmp_path / "ai"
        traj_dir = ai_dir / "trajectories"
        traj_dir.mkdir(parents=True)
        (traj_dir / "trajectory_0000.json").write_text(
            json.dumps({"outcome": "exit:task_complete", "messages": []})
        )
        (tmp_path / "cycles.out").write_text("")

        d = diagnose(tmp_path, sentry_available=False)
        assert "exit:task_complete" in d.evidence

    def test_no_files(self, tmp_path: Path):
        d = diagnose(tmp_path, sentry_available=False)
        assert d.source == "raw-artifacts"
        assert d.verdict == "HEALTHY"

    def test_custom_read_file_seam(self, tmp_path: Path):
        (tmp_path / "cycles.out").write_text("")

        def fake_read(p: Path) -> str:
            return "========== CYCLE 7  x ==========\n"

        d = diagnose(tmp_path, read_file=fake_read, sentry_available=False)
        assert d.cycles_started == [7]


# ---------------------------------------------------------------------------
# Cycle 14: additive founding fix-class fields (client-timeout + inner-wall)
# ---------------------------------------------------------------------------


class TestFoundingFixClassFields:
    def test_new_fields_default_none(self):
        d = Diagnosis()
        assert d.client_timeout_cycle is None
        assert d.inner_wall_kill_cycle is None
        assert d.heaviest_inner_duration is None

    def test_derive_inner_wall(self):
        d = Diagnosis(inner_wall_kill_cycle=11)
        assert d.failure_mode == "none"  # not derived until _derive runs
        from revolver.diagnosis import _derive_failure_mode

        assert _derive_failure_mode(d) == "inner-wall"

    def test_derive_client_timeout(self):
        from revolver.diagnosis import _derive_failure_mode

        d = Diagnosis(client_timeout_cycle=8)
        assert _derive_failure_mode(d) == "client-timeout"

    def test_inner_wall_takes_precedence_over_wall_kill(self):
        # The merge is present (inner-wall) so it is NOT wall-kill-no-merge.
        from revolver.diagnosis import _derive_failure_mode

        d = Diagnosis(inner_wall_kill_cycle=11, wall_kill_cycle=11)
        assert _derive_failure_mode(d) == "inner-wall"

    def test_existing_modes_unchanged(self):
        from revolver.diagnosis import _derive_failure_mode

        assert _derive_failure_mode(Diagnosis(driver_death_cycle=8)) == "driver-death"
        assert _derive_failure_mode(Diagnosis(wall_kill_cycle=5)) == "wall-kill"
        assert _derive_failure_mode(Diagnosis(stall_action="kill")) == "stall-kill"
        assert _derive_failure_mode(Diagnosis()) == "none"

    def test_action_needed_new_modes(self):
        assert Diagnosis(inner_wall_kill_cycle=11).action_needed is True
        assert Diagnosis(client_timeout_cycle=8).action_needed is True
        assert Diagnosis().action_needed is False

    def test_to_dict_from_dict_round_trip(self):
        d = Diagnosis(
            inner_wall_kill_cycle=11,
            client_timeout_cycle=8,
            heaviest_inner_duration=3200,
        )
        rt = Diagnosis.from_dict(d.to_dict())
        assert rt.inner_wall_kill_cycle == 11
        assert rt.client_timeout_cycle == 8
        assert rt.heaviest_inner_duration == 3200
        assert rt.to_dict() == d.to_dict()

    def test_old_dict_without_new_fields_still_loads(self):
        old = {
            "pipeline_id": "x",
            "failure_mode": "none",
            "sentry_exit_code": None,
        }
        d = Diagnosis.from_dict(old)
        assert d.inner_wall_kill_cycle is None
        assert d.client_timeout_cycle is None
        assert d.heaviest_inner_duration is None

    def test_outer_wall_and_inner_seconds_round_trip(self):
        d = Diagnosis(outer_wall=10800, inner_seconds=3000)
        rt = Diagnosis.from_dict(d.to_dict())
        assert rt.outer_wall == 10800
        assert rt.inner_seconds == 3000
        assert rt.to_dict() == d.to_dict()

    def test_outer_wall_and_inner_seconds_default_none(self):
        d = Diagnosis()
        assert d.outer_wall is None
        assert d.inner_seconds is None
