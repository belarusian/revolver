"""Tests for revolver.validation — pure, dry-run content validation of proposal
artifacts: check_syntax, check_imports, and validate_manifest_artifacts."""

from __future__ import annotations

import pytest

from revolver.diagnosis import Diagnosis
from revolver.launch_plan import LaunchPlan, build_launch_plan
from revolver.manifest import ProposalManifest, build_manifest
from revolver.proposal import PROPOSAL_NAMESPACE, NewFile, RepairProposal
from revolver.validation import (
    ImportReport,
    LaunchPlanReport,
    SyntaxReport,
    ValidationResult,
    check_imports,
    check_launch_plan,
    check_syntax,
    validate_manifest_artifacts,
    validate_manifest_launch,
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


def _manifest(new_files: list[NewFile], failure_mode: str = "driver-death") -> ProposalManifest:
    """Build a ProposalManifest carrying the given NEW files (bypassing builders)."""
    d = _diagnosis(failure_mode)
    proposal = RepairProposal(
        pipeline_id=d.pipeline_id,
        diagnosis=d,
        new_files=new_files,
    )
    plan = build_launch_plan(proposal)
    return ProposalManifest(
        pipeline_id=d.pipeline_id,
        diagnosis=d,
        proposal=proposal,
        launch_plan=plan,
    )


def _nf(path: str, content: str) -> NewFile:
    """Build a NewFile under the proposal namespace."""
    return NewFile(
        path=path,
        content=content,
        diff_from_predecessor="d",
        evidence="e",
    )


# ---------------------------------------------------------------------------
# check_syntax — .py must compile; non-python reported ok with a note
# ---------------------------------------------------------------------------


class TestCheckSyntax:
    def test_valid_python_ok(self):
        r = check_syntax("x = 1\n", path="revolver/fixes/a.py")
        assert isinstance(r, SyntaxReport)
        assert r.ok is True
        assert r.error == ""
        assert r.path == "revolver/fixes/a.py"

    def test_empty_python_ok(self):
        assert check_syntax("", path="a.py").ok is True

    def test_invalid_python_reports_error_with_path(self):
        r = check_syntax("def f(:\n", path="revolver/fixes/bad.py")
        assert r.ok is False
        assert "bad.py" in r.error
        assert "line 1" in r.error

    def test_non_python_out_reported_ok_with_note(self):
        r = check_syntax("= LAUNCH revolver driver-death =\n", path="revolver/fixes/x_cycles.out")
        assert r.ok is True
        assert r.error == "not python"

    def test_non_python_is_not_compiled(self):
        # content that would be a syntax error is still ok because it is not .py
        r = check_syntax("def f(:\n", path="revolver/fixes/x.out")
        assert r.ok is True
        assert r.error == "not python"

    def test_deterministic(self):
        a = check_syntax("def f(:\n", path="a.py")
        b = check_syntax("def f(:\n", path="a.py")
        assert a == b


# ---------------------------------------------------------------------------
# check_imports — stdlib + known modules resolve; the rest are missing
# ---------------------------------------------------------------------------


class TestCheckImports:
    def test_stdlib_import_ok(self):
        r = check_imports("import os\nimport collections\n", path="a.py")
        assert isinstance(r, ImportReport)
        assert r.ok is True
        assert r.missing == []

    def test_revolver_import_ok_by_default(self):
        r = check_imports("import revolver.diagnosis\n", path="a.py")
        assert r.ok is True
        assert r.missing == []

    def test_from_import_revolver_ok(self):
        r = check_imports("from revolver.proposal import NewFile\n", path="a.py")
        assert r.ok is True
        assert r.missing == []

    def test_unknown_import_missing(self):
        r = check_imports("import requests\n", path="a.py")
        assert r.ok is False
        assert r.missing == ["requests"]

    def test_multiple_unknown_sorted(self):
        r = check_imports("import zeta\nimport alpha\n", path="a.py")
        assert r.ok is False
        assert r.missing == ["alpha", "zeta"]

    def test_dotted_unknown_reports_top_level(self):
        r = check_imports("import foo.bar.baz\n", path="a.py")
        assert r.ok is False
        assert r.missing == ["foo"]

    def test_from_dotted_unknown_reports_top_level(self):
        r = check_imports("from foo.bar import baz\n", path="a.py")
        assert r.ok is False
        assert r.missing == ["foo"]

    def test_relative_import_skipped(self):
        r = check_imports("from . import sibling\nfrom ..pkg import thing\n", path="a.py")
        assert r.ok is True
        assert r.missing == []

    def test_no_imports_ok(self):
        r = check_imports("x = 1\n", path="a.py")
        assert r.ok is True
        assert r.missing == []

    def test_unparseable_content_ok(self):
        # a syntax error yields no import nodes -> nothing missing
        r = check_imports("def f(:\n", path="a.py")
        assert r.ok is True
        assert r.missing == []

    def test_custom_known_modules(self):
        r = check_imports("import requests\n", path="a.py", known_modules={"requests"})
        assert r.ok is True
        assert r.missing == []

    def test_custom_known_modules_replaces_default(self):
        # with a custom set, revolver is no longer known
        r = check_imports("import revolver\n", path="a.py", known_modules={"requests"})
        assert r.ok is False
        assert r.missing == ["revolver"]

    def test_deterministic(self):
        a = check_imports("import requests\n", path="a.py")
        b = check_imports("import requests\n", path="a.py")
        assert a == b


# ---------------------------------------------------------------------------
# validate_manifest_artifacts — one ValidationResult per NewFile
# ---------------------------------------------------------------------------


class TestValidateManifestArtifacts:
    def test_healthy_manifest_empty(self):
        m = _manifest([], failure_mode="none")
        assert validate_manifest_artifacts(m) == []

    def test_one_result_per_new_file_in_order(self):
        files = [
            _nf(PROPOSAL_NAMESPACE + "a.py", "x = 1\n"),
            _nf(PROPOSAL_NAMESPACE + "b.py", "y = 2\n"),
        ]
        m = _manifest(files)
        results = validate_manifest_artifacts(m)
        assert [r.path for r in results] == [files[0].path, files[1].path]
        assert all(isinstance(r, ValidationResult) for r in results)

    def test_valid_python_file_passes(self):
        m = _manifest([_nf(PROPOSAL_NAMESPACE + "ok.py", "import os\nx = 1\n")])
        r = validate_manifest_artifacts(m)[0]
        assert r.syntax_ok is True
        assert r.imports_ok is True
        assert r.errors == []

    def test_non_python_file_passes(self):
        m = _manifest([_nf(PROPOSAL_NAMESPACE + "m_cycles.out", "= LAUNCH x =\n")])
        r = validate_manifest_artifacts(m)[0]
        assert r.syntax_ok is True
        assert r.imports_ok is True
        assert r.errors == []

    def test_syntax_error_flagged(self):
        m = _manifest([_nf(PROPOSAL_NAMESPACE + "bad.py", "def f(:\n")])
        r = validate_manifest_artifacts(m)[0]
        assert r.syntax_ok is False
        assert r.imports_ok is True
        assert any(e.startswith("syntax:") for e in r.errors)

    def test_missing_import_flagged(self):
        m = _manifest([_nf(PROPOSAL_NAMESPACE + "imp.py", "import requests\n")])
        r = validate_manifest_artifacts(m)[0]
        assert r.syntax_ok is True
        assert r.imports_ok is False
        assert any("requests" in e for e in r.errors)

    def test_syntax_error_blocks_import_extraction(self):
        # a syntax error is flagged by check_syntax; check_imports cannot parse
        # the content, so it reports no missing imports (imports_ok stays True).
        m = _manifest([_nf(PROPOSAL_NAMESPACE + "both.py", "import requests\ndef f(:\n")])
        r = validate_manifest_artifacts(m)[0]
        assert r.syntax_ok is False
        assert r.imports_ok is True
        assert any(e.startswith("syntax:") for e in r.errors)
        assert not any(e.startswith("import:") for e in r.errors)

    def test_known_modules_override(self):
        m = _manifest([_nf(PROPOSAL_NAMESPACE + "imp.py", "import requests\n")])
        r = validate_manifest_artifacts(m, known_modules={"requests"})[0]
        assert r.imports_ok is True
        assert r.errors == []

    def test_real_builder_files_validate(self):
        # the concrete fix builders emit valid .py + .out files; all should pass
        from revolver.fixes import build_driver_death_fix

        files = build_driver_death_fix(_diagnosis("driver-death"))
        m = _manifest(files)
        results = validate_manifest_artifacts(m)
        assert len(results) == len(files)
        for res in results:
            assert res.syntax_ok is True
            assert res.imports_ok is True
            assert res.errors == []

    def test_deterministic(self):
        files = [_nf(PROPOSAL_NAMESPACE + "a.py", "import os\n")]
        m = _manifest(files)
        assert validate_manifest_artifacts(m) == validate_manifest_artifacts(m)


class TestAllFailureModes:
    def test_every_failure_mode_all_pass(self):
        # the briefing: validate_manifest_artifacts over every failure_mode
        # yields all-pass results (the concrete builders emit valid .py + .out).
        from revolver.fixes import FIX_BUILDERS

        for mode in ("driver-death", "wall-kill", "stall-kill", "none"):
            files = FIX_BUILDERS[mode](_diagnosis(mode))
            m = _manifest(files, failure_mode=mode)
            results = validate_manifest_artifacts(m)
            assert len(results) == len(files)
            for res in results:
                assert res.syntax_ok is True, (mode, res)
                assert res.imports_ok is True, (mode, res)
                assert res.errors == [], (mode, res)


# ---------------------------------------------------------------------------
# check_launch_plan — command-shape invariants (nohup, append, pin, budgets)
# ---------------------------------------------------------------------------


def _plan(**overrides) -> LaunchPlan:
    """A healthy, actionable LaunchPlan; override fields to break it."""
    base = dict(
        pipeline_id="revolver",
        command=(
            "nohup revolver launch --pipeline revolver --endpoint ep "
            "--failure-mode driver-death >> cycles.out 2>&1 &"
        ),
        cycles_out_append="= LAUNCH revolver driver-death =\n",
        endpoint_pin="ep",
        request_timeout=90,
        outer_wall=60,
        one_pipeline_per_endpoint=True,
        rationale="r",
        version="1.0",
    )
    base.update(overrides)
    return LaunchPlan(**base)


def _noop_plan() -> LaunchPlan:
    return LaunchPlan(
        pipeline_id="revolver",
        command="",
        cycles_out_append="",
        endpoint_pin="ep",
        request_timeout=0,
        outer_wall=0,
        one_pipeline_per_endpoint=True,
        rationale="no-op",
        version="1.0",
    )


class TestCheckLaunchPlan:
    def test_noop_is_ok_with_note(self):
        r = check_launch_plan(_noop_plan())
        assert isinstance(r, LaunchPlanReport)
        assert r.ok is True
        assert "no-op" in r.errors[0]

    def test_healthy_actionable_is_ok(self):
        r = check_launch_plan(_plan())
        assert r.ok is True
        assert r.errors == []

    def test_rejects_command_without_nohup(self):
        r = check_launch_plan(
            _plan(command="revolver launch --pipeline p --endpoint ep")
        )
        assert r.ok is False
        assert any("nohup" in e for e in r.errors)

    def test_rejects_empty_marker(self):
        r = check_launch_plan(_plan(cycles_out_append=""))
        assert r.ok is False
        assert any("non-empty" in e for e in r.errors)

    def test_rejects_marker_without_newline(self):
        r = check_launch_plan(_plan(cycles_out_append="= LAUNCH p ="))
        assert r.ok is False
        assert any("newline" in e for e in r.errors)

    def test_rejects_truncate_marker(self):
        r = check_launch_plan(_plan(cycles_out_append="> cycles.out\n"))
        assert r.ok is False
        assert any("append" in e and "truncate" in e for e in r.errors)

    def test_rejects_pin_mismatch(self):
        r = check_launch_plan(_plan(endpoint_pin="ep"), endpoint_pin="other")
        assert r.ok is False
        assert any("endpoint_pin" in e for e in r.errors)

    def test_self_consistency_pin_passes(self):
        # no expected pin supplied -> self-consistency check, always passes
        r = check_launch_plan(_plan(endpoint_pin="whatever"))
        assert r.ok is True

    def test_rejects_request_timeout_lt_outer_wall(self):
        r = check_launch_plan(_plan(request_timeout=30, outer_wall=60))
        assert r.ok is False
        assert any("request_timeout" in e for e in r.errors)

    def test_request_timeout_eq_outer_wall_is_ok(self):
        r = check_launch_plan(_plan(request_timeout=60, outer_wall=60))
        assert r.ok is True

    def test_rejects_one_pipeline_per_endpoint_false(self):
        r = check_launch_plan(_plan(one_pipeline_per_endpoint=False))
        assert r.ok is False
        assert any("one_pipeline_per_endpoint" in e for e in r.errors)

    def test_deterministic(self):
        assert check_launch_plan(_plan()) == check_launch_plan(_plan())


# ---------------------------------------------------------------------------
# validate_manifest_launch — every failure_mode ok; broken plan fails
# ---------------------------------------------------------------------------


class TestValidateManifestLaunch:
    @pytest.mark.parametrize(
        "failure_mode", ["driver-death", "wall-kill", "stall-kill", "none"]
    )
    def test_every_failure_mode_ok(self, failure_mode):
        m = build_manifest(_diagnosis(failure_mode))
        r = validate_manifest_launch(m)
        assert isinstance(r, LaunchPlanReport)
        assert r.ok is True, (failure_mode, r)

    def test_broken_plan_fails(self):
        m = build_manifest(_diagnosis("driver-death"))
        broken = LaunchPlan(
            pipeline_id=m.pipeline_id,
            command="revolver launch --pipeline p --endpoint ep",  # no nohup
            cycles_out_append="> cycles.out\n",  # truncate
            endpoint_pin="ep",
            request_timeout=30,
            outer_wall=60,  # request_timeout < outer_wall
            one_pipeline_per_endpoint=False,
            rationale="broken",
            version="1.0",
        )
        m.launch_plan = broken
        r = validate_manifest_launch(m)
        assert r.ok is False
        assert len(r.errors) >= 1

    def test_endpoint_pin_kwarg_forwarded(self):
        m = build_manifest(_diagnosis("driver-death"))
        # the real plan carries the diagnosis pin; a different expected pin fails
        r = validate_manifest_launch(m, endpoint_pin="not-the-pin")
        assert r.ok is False
        assert any("endpoint_pin" in e for e in r.errors)

    def test_deterministic(self):
        m = build_manifest(_diagnosis("wall-kill"))
        assert validate_manifest_launch(m) == validate_manifest_launch(m)
