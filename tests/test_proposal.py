"""Tests for revolver.proposal + revolver.fixes — propose() round-trip, the
additions-only contract (hard rule 7), and lossless to_dict/from_dict."""

from __future__ import annotations

import pytest

from revolver.diagnosis import Diagnosis
from revolver.fixes import (
    FIX_BUILDERS,
    build_driver_death_fix,
    build_none_fix,
    build_stall_kill_fix,
    build_wall_kill_fix,
)
from revolver.proposal import (
    PROPOSAL_NAMESPACE,
    PROPOSAL_VERSION,
    NewFile,
    RepairProposal,
    propose,
)


def _diagnosis(failure_mode: str) -> Diagnosis:
    """Build a minimal Diagnosis for a given failure_mode."""
    d = Diagnosis(failure_mode=failure_mode, source="sentry-report")
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
# propose() round-trip over every failure_mode
# ---------------------------------------------------------------------------


class TestPropose:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_yields_valid_proposal(self, failure_mode):
        d = _diagnosis(failure_mode)
        p = propose(d)
        assert isinstance(p, RepairProposal)
        assert p.pipeline_id == d.pipeline_id
        assert p.diagnosis.failure_mode == failure_mode
        assert p.version == PROPOSAL_VERSION
        # validate() must not raise
        p.validate()

    def test_none_yields_empty_new_files(self):
        p = propose(_diagnosis("none"))
        assert p.new_files == []
        assert "no action needed" in p.rationale

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_actionable_yields_new_files(self, failure_mode):
        p = propose(_diagnosis(failure_mode))
        assert len(p.new_files) >= 1
        assert failure_mode in p.rationale

    def test_deterministic(self):
        d = _diagnosis("driver-death")
        assert propose(d).to_dict() == propose(d).to_dict()

    def test_injectable_builders_seam(self):
        d = _diagnosis("driver-death")
        sentinel = NewFile(
            path=PROPOSAL_NAMESPACE + "sentinel.py",
            content="x",
            diff_from_predecessor="d",
            evidence="e",
        )
        p = propose(d, builders={"driver-death": lambda diag: [sentinel]})
        assert p.new_files == [sentinel]


# ---------------------------------------------------------------------------
# every new_file carries non-empty diff-from-predecessor + evidence
# ---------------------------------------------------------------------------


class TestNewFileContent:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_nonempty_diff_and_evidence(self, failure_mode):
        p = propose(_diagnosis(failure_mode))
        for nf in p.new_files:
            assert nf.diff_from_predecessor.strip()
            assert nf.evidence.strip()

    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill"]
    )
    def test_content_embeds_docstring(self, failure_mode):
        p = propose(_diagnosis(failure_mode))
        for nf in p.new_files:
            assert "Diff from predecessor:" in nf.content
            assert "Evidence:" in nf.content
            # the embedded statements match the structured fields
            assert nf.diff_from_predecessor in nf.content
            assert nf.evidence in nf.content


# ---------------------------------------------------------------------------
# hard rule 7 — never mutate an existing path
# ---------------------------------------------------------------------------


class TestHardRule7:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_all_paths_under_namespace(self, failure_mode):
        p = propose(_diagnosis(failure_mode))
        for nf in p.new_files:
            assert nf.path.startswith(PROPOSAL_NAMESPACE)

    def test_rejects_existing_path(self):
        d = _diagnosis("driver-death")
        p = propose(d)
        existing = {p.new_files[0].path}
        with pytest.raises(ValueError, match="already exists"):
            p.validate(existing_paths=existing)

    def test_rejects_path_outside_namespace(self):
        bad = NewFile(
            path="revolver/diagnosis.py",
            content="x",
            diff_from_predecessor="d",
            evidence="e",
        )
        p = RepairProposal(
            pipeline_id="revolver",
            diagnosis=_diagnosis("none"),
            new_files=[bad],
        )
        with pytest.raises(ValueError, match="hard rule 7"):
            p.validate()


# ---------------------------------------------------------------------------
# to_dict / from_dict lossless
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_proposal_round_trip(self, failure_mode):
        p = propose(_diagnosis(failure_mode))
        assert RepairProposal.from_dict(p.to_dict()) == p

    def test_newfile_round_trip(self):
        nf = NewFile(
            path=PROPOSAL_NAMESPACE + "x.py",
            content="c",
            diff_from_predecessor="d",
            evidence="e",
        )
        assert NewFile.from_dict(nf.to_dict()) == nf


# ---------------------------------------------------------------------------
# fix builders are pure + registry complete
# ---------------------------------------------------------------------------


class TestFixBuilders:
    def test_registry_covers_all_modes(self):
        assert set(FIX_BUILDERS) == {"driver-death", "wall-kill", "stall-kill", "client-timeout", "none"}

    def test_none_builder_empty(self):
        assert build_none_fix(_diagnosis("none")) == []

    def test_builders_pure_deterministic(self):
        d = _diagnosis("wall-kill")
        assert build_wall_kill_fix(d) == build_wall_kill_fix(d)
        d2 = _diagnosis("stall-kill")
        assert build_stall_kill_fix(d2) == build_stall_kill_fix(d2)
        d3 = _diagnosis("driver-death")
        assert build_driver_death_fix(d3) == build_driver_death_fix(d3)
