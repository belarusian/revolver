"""Tests for revolver.launch_plan — build_launch_plan() derivation, the
LaunchPlan invariants, lossless to_dict/from_dict, and validate() raising."""

from __future__ import annotations

import pytest

from revolver.diagnosis import Diagnosis
from revolver.launch_plan import (
    LAUNCH_PLAN_VERSION,
    LaunchPlan,
    build_launch_plan,
)
from revolver.proposal import propose


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
        d.stall_reason = "socket dead, inner pid 4242"
        d.live_work = True
        d.live_work_root = 4242
        d.evidence = "inner pid hung"
    else:
        d.evidence = "healthy"
    return d


# ---------------------------------------------------------------------------
# build_launch_plan() derivation over every failure_mode
# ---------------------------------------------------------------------------


class TestBuildLaunchPlan:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_yields_valid_plan(self, failure_mode):
        p = propose(_diagnosis(failure_mode))
        plan = build_launch_plan(p)
        assert isinstance(plan, LaunchPlan)
        assert plan.pipeline_id == p.pipeline_id
        assert plan.version == LAUNCH_PLAN_VERSION
        # validate() must not raise
        plan.validate()

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_actionable_has_command_and_marker(self, failure_mode):
        plan = build_launch_plan(propose(_diagnosis(failure_mode)))
        assert plan.command.strip()
        assert plan.cycles_out_append.strip()
        assert failure_mode in plan.command
        assert failure_mode in plan.cycles_out_append

    def test_healthy_is_noop(self):
        plan = build_launch_plan(propose(_diagnosis("none")))
        assert plan.command == ""
        assert plan.cycles_out_append == ""
        assert plan.request_timeout == 0
        assert plan.outer_wall == 0
        assert "no-op" in plan.rationale

    def test_endpoint_pin_verbatim(self):
        pin = "https://ep.example/42?token=abc"
        for fm in ["driver-death", "wall-kill", "stall-kill", "none"]:
            plan = build_launch_plan(propose(_diagnosis(fm, endpoint_pin=pin)))
            assert plan.endpoint_pin == pin

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_request_timeout_ge_outer_wall(self, failure_mode):
        plan = build_launch_plan(propose(_diagnosis(failure_mode)))
        assert plan.request_timeout >= plan.outer_wall

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_one_pipeline_per_endpoint(self, failure_mode):
        plan = build_launch_plan(propose(_diagnosis(failure_mode)))
        assert plan.one_pipeline_per_endpoint is True

    def test_deterministic(self):
        p = propose(_diagnosis("driver-death"))
        assert build_launch_plan(p).to_dict() == build_launch_plan(p).to_dict()

    def test_budgets_scale_with_cycle(self):
        d8 = _diagnosis("driver-death")
        d8.driver_death_cycle = 8
        d20 = _diagnosis("driver-death")
        d20.driver_death_cycle = 20
        p8 = build_launch_plan(propose(d8))
        p20 = build_launch_plan(propose(d20))
        assert p20.outer_wall > p8.outer_wall
        assert p20.request_timeout > p8.request_timeout
        # margin preserved
        assert p20.request_timeout - p20.outer_wall == p8.request_timeout - p8.outer_wall


# ---------------------------------------------------------------------------
# to_dict / from_dict lossless
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_launch_plan_round_trip(self, failure_mode):
        plan = build_launch_plan(propose(_diagnosis(failure_mode)))
        assert LaunchPlan.from_dict(plan.to_dict()) == plan

    def test_to_dict_keys(self):
        plan = build_launch_plan(propose(_diagnosis("wall-kill")))
        d = plan.to_dict()
        assert set(d) == {
            "pipeline_id",
            "command",
            "cycles_out_append",
            "endpoint_pin",
            "request_timeout",
            "outer_wall",
            "one_pipeline_per_endpoint",
            "rationale",
            "version",
        }


# ---------------------------------------------------------------------------
# validate() raises on invariant violation
# ---------------------------------------------------------------------------


class TestValidateRaises:
    def _plan(self, **overrides) -> LaunchPlan:
        base = {
            "pipeline_id": "revolver",
            "command": "cmd",
            "cycles_out_append": "marker\n",
            "endpoint_pin": "ep",
            "request_timeout": 90,
            "outer_wall": 60,
            "one_pipeline_per_endpoint": True,
            "rationale": "r",
            "version": LAUNCH_PLAN_VERSION,
        }
        base.update(overrides)
        return LaunchPlan(**base)

    def test_request_timeout_lt_outer_wall(self):
        with pytest.raises(ValueError, match="request_timeout"):
            self._plan(request_timeout=30, outer_wall=60).validate()

    def test_negative_outer_wall(self):
        with pytest.raises(ValueError, match="outer_wall"):
            self._plan(request_timeout=0, outer_wall=-1).validate()

    def test_negative_request_timeout(self):
        with pytest.raises(ValueError, match="request_timeout"):
            self._plan(request_timeout=-1, outer_wall=0).validate()

    def test_one_pipeline_per_endpoint_false(self):
        with pytest.raises(ValueError, match="one_pipeline_per_endpoint"):
            self._plan(one_pipeline_per_endpoint=False).validate()

    def test_empty_pipeline_id(self):
        with pytest.raises(ValueError, match="pipeline_id"):
            self._plan(pipeline_id="").validate()

    def test_empty_version(self):
        with pytest.raises(ValueError, match="version"):
            self._plan(version="").validate()

    def test_valid_plan_does_not_raise(self):
        assert self._plan().validate() is not None
