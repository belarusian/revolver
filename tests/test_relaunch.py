"""Tests for revolver.relaunch — first_not_done_cycle, plan_relaunch, and
verify_relaunch. All I/O and process probes go through injectable seams
(patch.object / explicit seam args); no real filesystem or process is touched."""

from __future__ import annotations

import pytest

from revolver.diagnosis import Diagnosis
from revolver.manifest import build_manifest
from revolver.relaunch import (
    RelaunchPlan,
    RelaunchVerification,
    first_not_done_cycle,
    plan_relaunch,
    verify_relaunch,
)


def _diagnosis(failure_mode: str, endpoint_pin: str = "ep-42") -> Diagnosis:
    """Build a minimal Diagnosis for a given failure_mode with a known pin."""
    d = Diagnosis(
        failure_mode=failure_mode,
        source="sentry-report",
        endpoint_pin=endpoint_pin,
    )
    if failure_mode == "driver-death":
        d.driver_death_cycle = 8
        d.driver_alive = False
        d.evidence = "driver process dead"
    elif failure_mode == "wall-kill":
        d.wall_kill_cycle = 5
        d.cycles_wall_kill = [5]
        d.evidence = "cycle wall-killed without merge"
    elif failure_mode == "stall-kill":
        d.stall_action = "kill"
        d.stall_reason = "socket dead"
        d.live_work = True
        d.live_work_root = 4242
        d.evidence = "inner pid hung"
    else:
        d.evidence = "healthy"
    return d


def _manifest(failure_mode: str = "driver-death") -> "object":
    """Build a validated manifest for a given failure_mode."""
    return build_manifest(_diagnosis(failure_mode))


# ---------------------------------------------------------------------------
# first_not_done_cycle
# ---------------------------------------------------------------------------


class TestFirstNotDoneCycle:
    def test_first_gap(self):
        # cycles 1..5, done 1,2 -> resume at 3
        assert first_not_done_cycle([1, 2, 3, 4, 5], done=[1, 2]) == 3

    def test_first_cycle_not_done(self):
        # nothing done -> resume at the smallest cycle
        assert first_not_done_cycle([4, 2, 7], done=[]) == 2

    def test_all_done_returns_none(self):
        assert first_not_done_cycle([1, 2, 3], done=[1, 2, 3]) is None

    def test_empty_cycles_returns_none(self):
        assert first_not_done_cycle([], done=[]) is None

    def test_out_of_order_input(self):
        # out-of-order cycles, done is a subset
        assert first_not_done_cycle([5, 1, 3, 2, 4], done=[1, 5]) == 2

    def test_duplicate_input(self):
        # duplicates are deduped; smallest not-done wins
        assert first_not_done_cycle([3, 3, 1, 1, 2], done=[1]) == 2

    def test_custom_done_seam(self):
        # done as a set (different collection type)
        assert first_not_done_cycle([1, 2, 3, 4], done={2, 3}) == 1

    def test_done_none_defaults_to_empty(self):
        # done=None -> nothing done -> smallest cycle
        assert first_not_done_cycle([9, 3, 7]) == 3

    def test_done_superset_of_cycles(self):
        # done contains cycles not in the cycle list; still returns None
        assert first_not_done_cycle([1, 2], done=[1, 2, 99]) is None


# ---------------------------------------------------------------------------
# plan_relaunch
# ---------------------------------------------------------------------------


class TestPlanRelaunch:
    def test_resume_from_first_not_done(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[1, 2, 3, 4, 5], done=[1, 2])
        assert isinstance(plan, RelaunchPlan)
        assert plan.first_cycle == 1
        assert plan.last_cycle == 5
        assert plan.resume_from == 3

    def test_all_done_is_noop(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[1, 2, 3], done=[1, 2, 3])
        assert plan.resume_from is None
        assert plan.command == ""
        assert "all done" in plan.note

    def test_empty_cycles_is_noop(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[], done=[])
        assert plan.resume_from is None
        assert plan.command == ""
        assert "all done" in plan.note

    def test_command_scoped_to_resume_range(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[1, 2, 3, 4, 5], done=[1, 2])
        # command must be scoped to resume_from..last_cycle
        assert "--cycles 3..5" in plan.command
        # reuses the launch-plan command shape: nohup + append-not-truncate
        assert plan.command.startswith("nohup revolver launch")
        assert ">> cycles.out 2>&1 &" in plan.command
        # carries the manifest identity
        assert m.pipeline_id in plan.command
        assert m.launch_plan.endpoint_pin in plan.command
        assert m.diagnosis.failure_mode in plan.command

    def test_command_shape_matches_launch_plan(self):
        m = _manifest("wall-kill")
        plan = plan_relaunch(m, cycles=[1, 2, 3], done=[])
        lp = m.launch_plan
        # same nohup/append shape as the original launch plan command
        assert lp.command.startswith("nohup revolver launch")
        assert plan.command.startswith("nohup revolver launch")
        assert ">> cycles.out 2>&1 &" in lp.command
        assert ">> cycles.out 2>&1 &" in plan.command

    def test_noop_note(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[1, 2], done=[1, 2])
        assert plan.note == "all done"

    def test_resume_note(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[1, 2, 3], done=[1])
        assert "resume from cycle 2 to 3" in plan.note

    def test_out_of_order_and_duplicates(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[5, 1, 3, 3, 2], done=[1, 5])
        assert plan.first_cycle == 1
        assert plan.last_cycle == 5
        assert plan.resume_from == 2
        assert "--cycles 2..5" in plan.command

    def test_round_trip(self):
        m = _manifest("driver-death")
        plan = plan_relaunch(m, cycles=[1, 2, 3], done=[1])
        assert RelaunchPlan.from_dict(plan.to_dict()) == plan


# ---------------------------------------------------------------------------
# verify_relaunch
# ---------------------------------------------------------------------------


class TestVerifyRelaunch:
    def test_marker_present_and_driver_alive_is_ok(self):
        m = _manifest("driver-death")
        marker = m.launch_plan.cycles_out_append
        result = verify_relaunch(
            m,
            read_cycles_out=lambda: "some line\n" + marker + "more\n",
            driver_alive=lambda: True,
        )
        assert isinstance(result, RelaunchVerification)
        assert result.ok is True
        assert result.marker_appended is True
        assert result.driver_alive is True
        assert result.errors == []

    def test_marker_missing_is_not_ok(self):
        m = _manifest("driver-death")
        result = verify_relaunch(
            m,
            read_cycles_out=lambda: "unrelated content\n",
            driver_alive=lambda: True,
        )
        assert result.ok is False
        assert result.marker_appended is False
        assert result.driver_alive is True
        assert any("marker" in e for e in result.errors)

    def test_driver_dead_is_not_ok(self):
        m = _manifest("driver-death")
        marker = m.launch_plan.cycles_out_append
        result = verify_relaunch(
            m,
            read_cycles_out=lambda: marker,
            driver_alive=lambda: False,
        )
        assert result.ok is False
        assert result.marker_appended is True
        assert result.driver_alive is False
        assert any("driver" in e for e in result.errors)

    def test_both_missing_is_not_ok(self):
        m = _manifest("driver-death")
        result = verify_relaunch(
            m,
            read_cycles_out=lambda: "",
            driver_alive=lambda: False,
        )
        assert result.ok is False
        assert result.marker_appended is False
        assert result.driver_alive is False
        assert len(result.errors) == 2

    def test_noop_plan_is_ok_and_probes_nothing(self):
        # A healthy diagnosis yields a no-op launch plan (empty command).
        m = _manifest("none")
        assert m.launch_plan.command == ""

        # Seams that would fail if called — proves they are NOT invoked.
        def _boom_read() -> str:
            raise AssertionError("read_cycles_out must not be called for no-op")

        def _boom_alive() -> bool:
            raise AssertionError("driver_alive must not be called for no-op")

        result = verify_relaunch(
            m,
            read_cycles_out=_boom_read,
            driver_alive=_boom_alive,
        )
        assert result.ok is True
        assert "no-op" in result.note
        assert result.errors == []

    def test_round_trip(self):
        m = _manifest("driver-death")
        marker = m.launch_plan.cycles_out_append
        result = verify_relaunch(
            m,
            read_cycles_out=lambda: marker,
            driver_alive=lambda: True,
        )
        assert RelaunchVerification.from_dict(result.to_dict()) == result

    def test_to_dict_keys(self):
        m = _manifest("driver-death")
        marker = m.launch_plan.cycles_out_append
        result = verify_relaunch(
            m,
            read_cycles_out=lambda: marker,
            driver_alive=lambda: True,
        )
        assert set(result.to_dict()) == {
            "ok",
            "marker_appended",
            "driver_alive",
            "errors",
            "note",
        }
