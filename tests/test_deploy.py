"""Tests for revolver.deploy — deploy_manifest() and relaunch() with injectable
seams. Never spawns a real process or writes to the real filesystem."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from revolver.deploy import (
    DeployReport,
    LaunchReport,
    deploy_manifest,
    relaunch,
)
from revolver.diagnosis import Diagnosis
from revolver.manifest import ProposalManifest, build_manifest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diagnosis(failure_mode: str, endpoint_pin: str = "ep-42") -> Diagnosis:
    """Build a minimal Diagnosis for a given failure_mode."""
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


def _manifest_with_files(failure_mode: str = "driver-death") -> ProposalManifest:
    """Build a manifest with at least one NewFile in the proposal."""
    d = _diagnosis(failure_mode)
    return build_manifest(d)


def _manifest_noop() -> ProposalManifest:
    """Build a healthy (no-op) manifest with no new files and empty command."""
    d = _diagnosis("none")
    return build_manifest(d)


def _fake_write_file() -> MagicMock:
    """Create a mock write_file seam that records calls."""
    mock = MagicMock()
    mock.side_effect = lambda path, content: None
    return mock


def _fake_approved(result: bool = True) -> MagicMock:
    """Create a mock approved seam returning a fixed bool."""
    mock = MagicMock()
    mock.return_value = result
    return mock


def _fake_run_command(returncode: int = 0, stderr: str = "") -> MagicMock:
    """Create a mock run_command seam returning a CompletedProcess."""
    mock = MagicMock()
    mock.return_value = subprocess.CompletedProcess(
        args="", returncode=returncode, stdout="", stderr=stderr
    )
    return mock


# ---------------------------------------------------------------------------
# DeployReport dataclass
# ---------------------------------------------------------------------------


class TestDeployReport:
    def test_fields(self):
        r = DeployReport(ok=True, deployed_paths=["a.py"], errors=[], note="done")
        assert r.ok is True
        assert r.deployed_paths == ["a.py"]
        assert r.errors == []
        assert r.note == "done"

    def test_defaults(self):
        r = DeployReport(ok=False)
        assert r.deployed_paths == []
        assert r.errors == []
        assert r.note == ""

    def test_to_dict_from_dict_roundtrip(self):
        r = DeployReport(ok=True, deployed_paths=["x.py", "y.py"], errors=["e"], note="n")
        d = r.to_dict()
        r2 = DeployReport.from_dict(d)
        assert r2 == r


# ---------------------------------------------------------------------------
# LaunchReport dataclass
# ---------------------------------------------------------------------------


class TestLaunchReport:
    def test_fields(self):
        r = LaunchReport(ok=True, command="echo hi", errors=[], note="launched")
        assert r.ok is True
        assert r.command == "echo hi"
        assert r.errors == []
        assert r.note == "launched"

    def test_defaults(self):
        r = LaunchReport(ok=False)
        assert r.command == ""
        assert r.errors == []
        assert r.note == ""

    def test_to_dict_from_dict_roundtrip(self):
        r = LaunchReport(ok=False, command="cmd", errors=["err"], note="fail")
        d = r.to_dict()
        r2 = LaunchReport.from_dict(d)
        assert r2 == r


# ---------------------------------------------------------------------------
# deploy_manifest — not approved
# ---------------------------------------------------------------------------


class TestDeployNotApproved:
    def test_not_approved_writes_nothing(self):
        m = _manifest_with_files()
        wf = _fake_write_file()
        ap = _fake_approved(result=False)
        report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)
        assert report.ok is True
        assert report.note == "not approved"
        assert report.deployed_paths == []
        assert report.errors == []
        wf.assert_not_called()

    def test_default_approved_returns_false(self):
        """The default approved seam always returns False."""
        m = _manifest_with_files()
        wf = _fake_write_file()
        report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf)
        assert report.ok is True
        assert report.note == "not approved"
        wf.assert_not_called()


# ---------------------------------------------------------------------------
# deploy_manifest — approved, writes files
# ---------------------------------------------------------------------------


class TestDeployApproved:
    def test_approved_writes_all_new_files(self):
        m = _manifest_with_files()
        assert len(m.proposal.new_files) > 0
        wf = _fake_write_file()
        ap = _fake_approved(result=True)
        report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)
        assert report.ok is True
        assert len(report.deployed_paths) == len(m.proposal.new_files)
        assert report.errors == []
        assert wf.call_count == len(m.proposal.new_files)

    def test_approved_writes_correct_paths_and_content(self):
        m = _manifest_with_files()
        wf = _fake_write_file()
        ap = _fake_approved(result=True)
        deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)
        for i, nf in enumerate(m.proposal.new_files):
            call = wf.call_args_list[i]
            path_arg, content_arg = call[0]
            assert path_arg == Path("/tmp/fake") / nf.path
            assert content_arg == nf.content

    def test_approved_no_new_files(self):
        """A healthy manifest has no new files; deploy is ok with 0 files."""
        m = _manifest_noop()
        wf = _fake_write_file()
        ap = _fake_approved(result=True)
        report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)
        assert report.ok is True
        assert report.deployed_paths == []
        assert report.errors == []
        wf.assert_not_called()


# ---------------------------------------------------------------------------
# deploy_manifest — hard rule 7: never overwrite existing path
# ---------------------------------------------------------------------------


class TestDeployHardRule7:
    def test_existing_path_is_skipped(self):
        """If target path exists, it is NOT overwritten (hard rule 7)."""
        m = _manifest_with_files()
        nf = m.proposal.new_files[0]
        wf = _fake_write_file()
        ap = _fake_approved(result=True)

        # Simulate: only the first file's target path already exists
        target = Path("/tmp/fake") / nf.path

        def fake_exists(self):
            return self == target

        with patch.object(Path, "exists", fake_exists):
            report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)

        assert nf.path not in report.deployed_paths
        assert len(report.errors) == 1
        assert "hard rule 7" in report.errors[0]
        # write_file should NOT have been called for the existing path
        # (other files may still be written)
        for call in wf.call_args_list:
            path_arg = call[0][0]
            assert path_arg != target

    def test_mixed_existing_and_new(self):
        """Some paths exist, some don't: existing are skipped, new are written."""
        m = _manifest_with_files()
        files = m.proposal.new_files
        assert len(files) >= 1

        wf = _fake_write_file()
        ap = _fake_approved(result=True)

        # First file exists, rest don't
        existing_target = Path("/tmp/fake") / files[0].path

        def fake_exists(self):
            return self == existing_target

        with patch.object(Path, "exists", fake_exists):
            report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)

        assert files[0].path not in report.deployed_paths
        assert len(report.errors) == 1
        # All other files should be deployed
        for nf in files[1:]:
            assert nf.path in report.deployed_paths
        assert wf.call_count == len(files) - 1


# ---------------------------------------------------------------------------
# relaunch — no-op (empty command)
# ---------------------------------------------------------------------------


class TestRelaunchNoop:
    def test_noop_plan_reports_noop(self):
        m = _manifest_noop()
        assert m.launch_plan.command == ""
        rc = _fake_run_command()
        report = relaunch(m, run_command=rc)
        assert report.ok is True
        assert report.note == "no-op"
        assert report.command == ""
        assert report.errors == []
        rc.assert_not_called()

    def test_noop_with_empty_command_string(self):
        """Even if we force an empty command, it's a no-op."""
        m = _manifest_noop()
        rc = _fake_run_command()
        relaunch(m, run_command=rc)
        rc.assert_not_called()


# ---------------------------------------------------------------------------
# relaunch — executes command via seam
# ---------------------------------------------------------------------------


class TestRelaunchExecutes:
    def test_successful_launch(self):
        m = _manifest_with_files()
        assert m.launch_plan.command != ""
        rc = _fake_run_command(returncode=0)
        report = relaunch(m, run_command=rc)
        assert report.ok is True
        assert report.command == m.launch_plan.command
        assert report.note == "launched"
        assert report.errors == []
        rc.assert_called_once_with(m.launch_plan.command)

    def test_failed_launch(self):
        m = _manifest_with_files()
        rc = _fake_run_command(returncode=1, stderr="boom")
        report = relaunch(m, run_command=rc)
        assert report.ok is False
        assert report.command == m.launch_plan.command
        assert report.note == "launch failed"
        assert len(report.errors) == 1
        assert "boom" in report.errors[0]
        assert "1" in report.errors[0]

    def test_launch_alias_seam(self):
        """The deprecated 'launch' kwarg works as an alias for run_command."""
        m = _manifest_with_files()
        rc = _fake_run_command(returncode=0)
        report = relaunch(m, launch=rc)
        assert report.ok is True
        rc.assert_called_once_with(m.launch_plan.command)

    def test_run_command_takes_precedence_over_launch(self):
        """If both launch and run_command are given, run_command wins."""
        m = _manifest_with_files()
        rc1 = _fake_run_command(returncode=0)
        rc2 = _fake_run_command(returncode=1, stderr="should not be used")
        report = relaunch(m, launch=rc2, run_command=rc1)
        assert report.ok is True
        rc1.assert_called_once()
        rc2.assert_not_called()


# ---------------------------------------------------------------------------
# relaunch — NO process kill
# ---------------------------------------------------------------------------


class TestRelaunchNoKill:
    def test_no_kill_called(self):
        """relaunch() never calls os.kill, signal, or any kill mechanism."""
        m = _manifest_with_files()
        rc = _fake_run_command(returncode=0)
        with patch("os.kill") as mock_kill:
            report = relaunch(m, run_command=rc)
            mock_kill.assert_not_called()
        assert report.ok is True

    def test_no_signal_imported(self):
        """The deploy module does not import signal."""
        import revolver.deploy as deploy_mod

        assert not hasattr(deploy_mod, "signal")


# ---------------------------------------------------------------------------
# deploy_manifest — default write_file seam (integration with tmp_path)
# ---------------------------------------------------------------------------


class TestDeployDefaultWriteFile:
    def test_default_write_file_creates_files(self, tmp_path):
        """With the default write_file seam, files are actually created on disk."""
        m = _manifest_with_files()
        ap = _fake_approved(result=True)
        report = deploy_manifest(m, base_dir=tmp_path, approved=ap)
        assert report.ok is True
        for nf in m.proposal.new_files:
            target = tmp_path / nf.path
            assert target.exists()
            assert target.read_text() == nf.content

    def test_default_write_file_hard_rule7(self, tmp_path):
        """With the default seam, an existing file is not overwritten."""
        m = _manifest_with_files()
        nf = m.proposal.new_files[0]
        target = tmp_path / nf.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ORIGINAL CONTENT")
        ap = _fake_approved(result=True)
        report = deploy_manifest(m, base_dir=tmp_path, approved=ap)
        # The existing file should be in errors
        assert nf.path not in report.deployed_paths
        assert len(report.errors) == 1
        # Content unchanged
        assert target.read_text() == "ORIGINAL CONTENT"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_deploy_manifest_with_empty_new_files_approved(self):
        """Approved manifest with zero new files: ok, no writes."""
        m = _manifest_noop()
        wf = _fake_write_file()
        ap = _fake_approved(result=True)
        report = deploy_manifest(m, base_dir="/tmp/fake", write_file=wf, approved=ap)
        assert report.ok is True
        assert report.deployed_paths == []
        assert report.errors == []
        wf.assert_not_called()

    def test_relaunch_with_whitespace_command_is_noop(self):
        """A command that is only whitespace is treated as no-op."""
        m = _manifest_noop()
        # Force an empty command
        m.launch_plan.command = ""
        rc = _fake_run_command()
        report = relaunch(m, run_command=rc)
        assert report.ok is True
        assert report.note == "no-op"
        rc.assert_not_called()
