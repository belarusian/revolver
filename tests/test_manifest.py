"""Tests for revolver.manifest — build_manifest() composition, the whole-manifest
validate() choke point, deterministic render(), and lossless to_dict/from_dict."""

from __future__ import annotations

import pytest

from revolver.diagnosis import Diagnosis
from revolver.launch_plan import build_launch_plan
from revolver.manifest import (
    MANIFEST_VERSION,
    ProposalManifest,
    build_manifest,
)
from revolver.proposal import (
    PROPOSAL_NAMESPACE,
    NewFile,
    RepairProposal,
    propose,
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
        d.stall_reason = "socket dead, inner pid 4242"
        d.live_work = True
        d.live_work_root = 4242
        d.evidence = "inner pid hung"
    else:
        d.evidence = "healthy"
    return d


# ---------------------------------------------------------------------------
# build_manifest() composition over every failure_mode
# ---------------------------------------------------------------------------


class TestBuildManifest:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_yields_valid_manifest(self, failure_mode):
        d = _diagnosis(failure_mode)
        m = build_manifest(d)
        assert isinstance(m, ProposalManifest)
        assert m.pipeline_id == d.pipeline_id
        assert m.version == MANIFEST_VERSION
        assert m.diagnosis.failure_mode == failure_mode
        # validate() must not raise
        m.validate()

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_composes_propose_and_build_launch_plan(self, failure_mode):
        d = _diagnosis(failure_mode)
        m = build_manifest(d)
        # the manifest composes the two existing pure derivations
        assert m.proposal == propose(d)
        assert m.launch_plan == build_launch_plan(propose(d))

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_actionable_has_new_files_and_command(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        assert len(m.proposal.new_files) >= 1
        assert m.launch_plan.command.strip()
        assert failure_mode in m.launch_plan.command

    def test_healthy_is_empty_path_and_noop_plan(self):
        m = build_manifest(_diagnosis("none"))
        assert m.proposal.new_files == []
        assert m.launch_plan.command == ""
        assert m.launch_plan.cycles_out_append == ""
        assert m.launch_plan.request_timeout == 0
        assert m.launch_plan.outer_wall == 0

    def test_deterministic(self):
        d = _diagnosis("driver-death")
        assert build_manifest(d).to_dict() == build_manifest(d).to_dict()

    def test_injectable_builders_seam(self):
        d = _diagnosis("driver-death")
        sentinel = NewFile(
            path=PROPOSAL_NAMESPACE + "sentinel.py",
            content="x",
            diff_from_predecessor="d",
            evidence="e",
        )
        m = build_manifest(d, builders={"driver-death": lambda diag: [sentinel]})
        assert m.proposal.new_files == [sentinel]


# ---------------------------------------------------------------------------
# whole-manifest validate() — the single choke point
# ---------------------------------------------------------------------------


class TestValidate:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_good_manifest_passes(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        assert m.validate() is m

    def test_rejects_out_of_namespace_path(self):
        d = _diagnosis("driver-death")
        bad = NewFile(
            path="revolver/diagnosis.py",
            content="x",
            diff_from_predecessor="d",
            evidence="e",
        )
        proposal = RepairProposal(
            pipeline_id=d.pipeline_id,
            diagnosis=d,
            new_files=[bad],
        )
        plan = build_launch_plan(proposal)
        m = ProposalManifest(
            pipeline_id=d.pipeline_id,
            diagnosis=d,
            proposal=proposal,
            launch_plan=plan,
        )
        with pytest.raises(ValueError, match="hard rule 7"):
            m.validate()

    def test_rejects_existing_path(self):
        d = _diagnosis("driver-death")
        m = build_manifest(d)
        existing = {m.proposal.new_files[0].path}
        with pytest.raises(ValueError, match="already exists"):
            m.validate(existing_paths=existing)

    def test_rejects_request_timeout_lt_outer_wall(self):
        d = _diagnosis("driver-death")
        proposal = propose(d)
        plan = build_launch_plan(proposal)
        # break the launch invariant: request_timeout < outer_wall
        plan.request_timeout = plan.outer_wall - 1
        m = ProposalManifest(
            pipeline_id=d.pipeline_id,
            diagnosis=d,
            proposal=proposal,
            launch_plan=plan,
        )
        with pytest.raises(ValueError, match="request_timeout"):
            m.validate()

    def test_rejects_one_pipeline_per_endpoint_false(self):
        d = _diagnosis("driver-death")
        proposal = propose(d)
        plan = build_launch_plan(proposal)
        plan.one_pipeline_per_endpoint = False
        m = ProposalManifest(
            pipeline_id=d.pipeline_id,
            diagnosis=d,
            proposal=proposal,
            launch_plan=plan,
        )
        with pytest.raises(ValueError, match="one_pipeline_per_endpoint"):
            m.validate()


# ---------------------------------------------------------------------------
# render() — deterministic, human-readable, embeds paths + launch command
# ---------------------------------------------------------------------------


class TestRender:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_deterministic(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        assert m.render() == m.render()

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_embeds_each_file_path(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        text = m.render()
        for nf in m.proposal.new_files:
            assert nf.path in text

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_embeds_launch_command(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        text = m.render()
        assert m.launch_plan.command in text

    def test_embeds_failure_mode_and_verdict(self):
        m = build_manifest(_diagnosis("wall-kill"))
        text = m.render()
        assert "wall-kill" in text
        assert m.diagnosis.verdict in text

    def test_healthy_render_has_noop(self):
        m = build_manifest(_diagnosis("none"))
        text = m.render()
        assert "no new files" in text
        assert "(none; no-op)" in text

    def test_render_stable_across_round_trip(self):
        m = build_manifest(_diagnosis("driver-death"))
        reloaded = ProposalManifest.from_dict(m.to_dict())
        assert reloaded.render() == m.render()


# ---------------------------------------------------------------------------
# to_dict / from_dict lossless
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_manifest_round_trip(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        assert ProposalManifest.from_dict(m.to_dict()) == m

    def test_to_dict_keys(self):
        m = build_manifest(_diagnosis("wall-kill"))
        d = m.to_dict()
        assert set(d) == {
            "pipeline_id",
            "diagnosis",
            "proposal",
            "launch_plan",
            "version",
        }
