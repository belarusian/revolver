"""revolver.relaunch — deterministic relaunch planning and verification.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: cycles 3-5 landed the pure derivations (propose, build_launch_plan,
build_manifest) and cycle 8-9 landed deploy/relaunch execution. This module
adds the *planning* and *verification* layer for relaunch: given a manifest
and the set of cycles that exist, derive where to resume (first not-done
cycle) and verify that a prior relaunch actually landed (marker in
cycles.out + driver alive).

All functions are pure, deterministic, stdlib-only, and use overridable
seams so tests never touch the real filesystem or spawn a real process.
NO process kill is performed anywhere in this module.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from revolver.manifest import ProposalManifest


# ---------------------------------------------------------------------------
# first_not_done_cycle
# ---------------------------------------------------------------------------


def first_not_done_cycle(
    cycles: Collection[int],
    *,
    done: Collection[int] | None = None,
) -> int | None:
    """Return the smallest cycle number in *cycles* that is NOT in *done*.

    This is the resume point: the first cycle that still needs work.

    Args:
        cycles: Collection of cycle numbers that exist (may be out-of-order
            or contain duplicates).
        done: Collection of cycle numbers already completed. If None, an
            empty set is used (i.e. nothing is done yet).

    Returns:
        The smallest cycle in *cycles* not in *done*, or None if all cycles
        are done (or *cycles* is empty).
    """
    if not cycles:
        return None
    done_set = set(done) if done is not None else set()
    # Sort and dedupe the input cycles
    unique_cycles = sorted(set(cycles))
    for c in unique_cycles:
        if c not in done_set:
            return c
    return None


# ---------------------------------------------------------------------------
# RelaunchPlan
# ---------------------------------------------------------------------------


@dataclass
class RelaunchPlan:
    """A typed relaunch plan scoped to a cycle range.

    Attributes:
        first_cycle: The first cycle in the full range.
        last_cycle: The last cycle in the full range.
        resume_from: The cycle to resume from (first not-done), or None for
            a no-op plan.
        command: The shell command to execute (empty for a no-op plan).
        note: Free-text note (e.g. "all done" for a no-op plan).
    """

    first_cycle: int
    last_cycle: int
    resume_from: int | None
    command: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "first_cycle": self.first_cycle,
            "last_cycle": self.last_cycle,
            "resume_from": self.resume_from,
            "command": self.command,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelaunchPlan:
        """Reconstruct a RelaunchPlan from a dict produced by :meth:`to_dict`."""
        return cls(
            first_cycle=data["first_cycle"],
            last_cycle=data["last_cycle"],
            resume_from=data["resume_from"],
            command=data["command"],
            note=data["note"],
        )


def plan_relaunch(
    manifest: ProposalManifest,
    *,
    cycles: Collection[int],
    done: Collection[int] | None = None,
) -> RelaunchPlan:
    """Derive a deterministic relaunch plan from a manifest and cycle set.

    The plan scopes the launch command to ``resume_from..last_cycle`` using
    the same command shape as ``manifest.launch_plan.command`` (nohup,
    append-not-truncate to cycles.out). Budgets are NOT re-derived; the
    existing launch plan's budgets are carried through implicitly.

    Args:
        manifest: The validated ProposalManifest (provides pipeline_id,
            endpoint_pin, failure_mode, and the command shape).
        cycles: Collection of all cycle numbers that exist.
        done: Collection of cycle numbers already completed (seam). If None,
            defaults to an empty set.

    Returns:
        A RelaunchPlan. If all cycles are done (resume_from is None), the
        plan is a no-op: empty command and "all done" note.
    """
    unique_cycles = sorted(set(cycles))
    if not unique_cycles:
        return RelaunchPlan(
            first_cycle=0,
            last_cycle=0,
            resume_from=None,
            command="",
            note="all done",
        )

    first_cycle = unique_cycles[0]
    last_cycle = unique_cycles[-1]
    resume_from = first_not_done_cycle(cycles, done=done)

    if resume_from is None:
        return RelaunchPlan(
            first_cycle=first_cycle,
            last_cycle=last_cycle,
            resume_from=None,
            command="",
            note="all done",
        )

    # Reuse the command shape from manifest.launch_plan.command:
    #   nohup revolver launch --pipeline <id> --endpoint <pin> --failure-mode <fm> >> cycles.out 2>&1 &
    # Scoped to the resume range.
    lp = manifest.launch_plan
    command = (
        f"nohup revolver launch --pipeline {manifest.pipeline_id} "
        f"--endpoint {lp.endpoint_pin} --failure-mode {manifest.diagnosis.failure_mode} "
        f"--cycles {resume_from}..{last_cycle} "
        f">> cycles.out 2>&1 &"
    )

    return RelaunchPlan(
        first_cycle=first_cycle,
        last_cycle=last_cycle,
        resume_from=resume_from,
        command=command,
        note=f"resume from cycle {resume_from} to {last_cycle}",
    )


# ---------------------------------------------------------------------------
# RelaunchVerification
# ---------------------------------------------------------------------------


@dataclass
class RelaunchVerification:
    """Result of a verify_relaunch() call.

    Attributes:
        ok: True if the relaunch is verified (marker present AND driver alive),
            or if the plan is a no-op.
        marker_appended: True if the cycles_out_append marker was found in
            cycles.out.
        driver_alive: True if the driver process is alive.
        errors: List of error messages (empty on success).
        note: Free-text note.
    """

    ok: bool
    marker_appended: bool
    driver_alive: bool
    errors: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "ok": self.ok,
            "marker_appended": self.marker_appended,
            "driver_alive": self.driver_alive,
            "errors": list(self.errors),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelaunchVerification:
        """Reconstruct a RelaunchVerification from a dict produced by :meth:`to_dict`."""
        return cls(
            ok=data["ok"],
            marker_appended=data["marker_appended"],
            driver_alive=data["driver_alive"],
            errors=list(data["errors"]),
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# Default seams
# ---------------------------------------------------------------------------


def _default_read_cycles_out() -> str:
    """Default read_cycles_out seam: read the real cycles.out file."""
    path = Path("cycles.out")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _default_driver_alive() -> bool:
    """Default driver_alive seam: probe the real driver process.

    Uses a lightweight check: look for a process matching the pipeline
    pattern. Returns False if no such process is found.
    """
    # Scan /proc for a process whose cmdline matches the launch pattern.
    # In practice this default is only used in production; tests always
    # inject a seam.
    try:
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                cmdline = (pid_dir / "cmdline").read_bytes().decode("utf-8", errors="replace")
                if "revolver" in cmdline and "launch" in cmdline:
                    return True
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return False


# ---------------------------------------------------------------------------
# verify_relaunch
# ---------------------------------------------------------------------------


def verify_relaunch(
    manifest: ProposalManifest,
    *,
    read_cycles_out: Callable[[], str] | None = None,
    driver_alive: Callable[[], bool] | None = None,
) -> RelaunchVerification:
    """Verify that a prior relaunch actually landed.

    Checks two conditions:
      1. The marker line (``manifest.launch_plan.cycles_out_append``) is
         present in cycles.out.
      2. The driver process is alive.

    A no-op plan (empty command in the launch plan) short-circuits: ok=True
    with note "all done / no-op" and no probes are performed.

    NO process kill is performed.

    Args:
        manifest: The validated ProposalManifest to verify.
        read_cycles_out: Overridable seam that returns the text content of
            cycles.out. Defaults to reading the real file.
        driver_alive: Overridable seam that returns True if the driver
            process is alive. Defaults to a real process probe.

    Returns:
        A RelaunchVerification.
    """
    lp = manifest.launch_plan

    # No-op plan: empty command means nothing was launched; no probes needed.
    if not lp.command:
        return RelaunchVerification(
            ok=True,
            marker_appended=False,
            driver_alive=False,
            errors=[],
            note="all done / no-op",
        )

    # Resolve seams
    if read_cycles_out is None:
        read_cycles_out = _default_read_cycles_out
    if driver_alive is None:
        driver_alive = _default_driver_alive

    errors: list[str] = []

    # Check 1: marker present in cycles.out
    cycles_out_text = read_cycles_out()
    marker = lp.cycles_out_append
    marker_appended = bool(marker) and marker.strip() in cycles_out_text
    if not marker_appended:
        errors.append(
            f"marker not found in cycles.out: {marker.strip()!r}"
        )

    # Check 2: driver alive
    is_alive = driver_alive()
    if not is_alive:
        errors.append("driver process not alive")

    ok = marker_appended and is_alive
    if ok:
        note = "relaunch verified: marker present and driver alive"
    else:
        note = "relaunch verification failed"

    return RelaunchVerification(
        ok=ok,
        marker_appended=marker_appended,
        driver_alive=is_alive,
        errors=errors,
        note=note,
    )
