"""revolver.deploy — deployment and relaunch execution for ProposalManifest.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: cycles 3-5 landed the pure derivations (propose, build_launch_plan,
build_manifest) on main. This module is the execution phase (cycles 8-9): it
takes a validated ProposalManifest and either deploys its new files to disk
(additions-only, hard rule 7) or relaunches its launch plan. Both operations
are gated behind overridable seams so tests never touch the real filesystem or
spawn a real process.

Hard rule 7: never overwrite an existing path. If a target path already exists
on disk, the file is skipped and an error is recorded.

Deterministic, stdlib-only. No process kill.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from revolver.manifest import ProposalManifest


# ---------------------------------------------------------------------------
# DeployReport
# ---------------------------------------------------------------------------


@dataclass
class DeployReport:
    """Result of a deploy_manifest() call.

    Attributes:
        ok: True if the operation completed without errors (including the
            not-approved no-op case).
        deployed_paths: List of repo-relative paths that were actually written.
        errors: List of error messages (empty on success).
        note: Free-text note (e.g. "not approved", "all files deployed").
    """

    ok: bool
    deployed_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "ok": self.ok,
            "deployed_paths": list(self.deployed_paths),
            "errors": list(self.errors),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeployReport:
        """Reconstruct a DeployReport from a dict produced by :meth:`to_dict`."""
        return cls(
            ok=data["ok"],
            deployed_paths=list(data["deployed_paths"]),
            errors=list(data["errors"]),
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# LaunchReport
# ---------------------------------------------------------------------------


@dataclass
class LaunchReport:
    """Result of a relaunch() call.

    Attributes:
        ok: True if the operation completed without errors (including the
            no-op case).
        command: The command that was (or would have been) executed.
        errors: List of error messages (empty on success).
        note: Free-text note (e.g. "no-op", "launched").
    """

    ok: bool
    command: str = ""
    errors: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "ok": self.ok,
            "command": self.command,
            "errors": list(self.errors),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LaunchReport:
        """Reconstruct a LaunchReport from a dict produced by :meth:`to_dict`."""
        return cls(
            ok=data["ok"],
            command=data["command"],
            errors=list(data["errors"]),
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# Default seams
# ---------------------------------------------------------------------------


def _default_write_file(path: Path, content: str) -> None:
    """Default write_file seam: write content to path using real open()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _default_approved() -> bool:
    """Default approved seam: always returns False (no human approval by default)."""
    return False


def _default_run_command(command: str) -> subprocess.CompletedProcess[str]:
    """Default run_command seam: execute command via real subprocess."""
    return subprocess.run(command, shell=True, capture_output=True, text=True, check=False)


# ---------------------------------------------------------------------------
# deploy_manifest
# ---------------------------------------------------------------------------


def deploy_manifest(
    manifest: ProposalManifest,
    *,
    base_dir: str | Path,
    write_file: Callable[[Path, str], None] | None = None,
    approved: Callable[[], bool] | None = None,
) -> DeployReport:
    """Deploy every NewFile in manifest.proposal.new_files to base_dir/<path>.

    Additions-only (hard rule 7): if the target path already exists on disk,
    the file is NOT written and an error is recorded.

    Args:
        manifest: The validated ProposalManifest to deploy.
        base_dir: Root directory under which files are written.
        write_file: Overridable seam for writing a file. Signature:
            (path: Path, content: str) -> None. Defaults to real open(..., 'w').
        approved: Overridable seam for human approval. A zero-arg callable
            returning bool. Defaults to a callable that always returns False.

    Returns:
        A DeployReport. If not approved, ok=True with note='not approved' and
        no files are written. If approved, each new file is written unless the
        target already exists (hard rule 7 violation -> error recorded).
    """
    if write_file is None:
        write_file = _default_write_file
    if approved is None:
        approved = _default_approved

    # Check approval first
    if not approved():
        return DeployReport(
            ok=True,
            deployed_paths=[],
            errors=[],
            note="not approved",
        )

    base = Path(base_dir)
    deployed_paths: list[str] = []
    errors: list[str] = []

    for nf in manifest.proposal.new_files:
        target = base / nf.path
        # Hard rule 7: never overwrite an existing path
        if target.exists():
            errors.append(
                f"hard rule 7 violated: {nf.path!r} already exists at {target}; "
                f"skipping (additions-only)"
            )
            continue
        write_file(target, nf.content)
        deployed_paths.append(nf.path)

    if errors:
        note = f"deployed {len(deployed_paths)}/{len(manifest.proposal.new_files)} files; {len(errors)} error(s)"
        ok = len(deployed_paths) > 0 or len(manifest.proposal.new_files) == 0
    else:
        note = f"all {len(deployed_paths)} file(s) deployed"
        ok = True

    return DeployReport(
        ok=ok,
        deployed_paths=deployed_paths,
        errors=errors,
        note=note,
    )


# ---------------------------------------------------------------------------
# relaunch
# ---------------------------------------------------------------------------


def relaunch(
    manifest: ProposalManifest,
    *,
    launch: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
    run_command: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
) -> LaunchReport:
    """Execute manifest.launch_plan.command via an overridable run_command seam.

    A no-op plan (empty command) is reported ok with a 'no-op' note and
    launches nothing. NO process kill is performed.

    Args:
        manifest: The validated ProposalManifest to relaunch.
        launch: Deprecated alias for run_command (kept for API compatibility).
        run_command: Overridable seam for executing the command. Signature:
            (command: str) -> subprocess.CompletedProcess[str]. Defaults to
            real subprocess.run(shell=True).

    Returns:
        A LaunchReport. If the command is empty, ok=True with note='no-op'.
        If the command executes successfully (returncode == 0), ok=True.
        If the command fails (returncode != 0), ok=False with stderr in errors.
    """
    # Resolve the seam: prefer run_command, fall back to launch, then default
    if run_command is not None:
        seam = run_command
    elif launch is not None:
        seam = launch
    else:
        seam = _default_run_command

    command = manifest.launch_plan.command

    # No-op plan: empty command means nothing to launch
    if not command:
        return LaunchReport(
            ok=True,
            command="",
            errors=[],
            note="no-op",
        )

    result = seam(command)

    if result.returncode == 0:
        return LaunchReport(
            ok=True,
            command=command,
            errors=[],
            note="launched",
        )
    else:
        stderr = result.stderr.strip() if result.stderr else ""
        return LaunchReport(
            ok=False,
            command=command,
            errors=[f"command exited with code {result.returncode}: {stderr}"],
            note="launch failed",
        )
