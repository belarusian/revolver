"""revolver.launch_plan — deterministic dry-run launch-plan derivation.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: the package contract (revolver/__init__.py) states that deployment/
relaunch is a later phase (cycles 8-9) and that every generated artifact is NEW
and additions-only. A launch plan is the dry-run, side-effect-free derivation of
*what would be launched* for a given :class:`~revolver.proposal.RepairProposal`:
the command line, the cycles.out marker to append, the endpoint pin (verbatim),
and the two wall-clock budgets (request_timeout, outer_wall). Nothing here writes
to disk or launches a process.

House invariants enforced by :meth:`LaunchPlan.validate`:
  * one pipeline per endpoint (``one_pipeline_per_endpoint`` is always True);
  * ``request_timeout >= outer_wall`` (the per-request budget never undercuts the
    outer wall-clock budget);
  * non-negative budgets, non-empty pipeline_id and version.

Deterministic, stdlib-only, pure functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from revolver.diagnosis import Diagnosis

if TYPE_CHECKING:
    from revolver.proposal import RepairProposal

# The launch-plan schema version (bumped when the to_dict shape changes).
LAUNCH_PLAN_VERSION = "1.0"

# Deterministic budget derivation constants (seconds).
_OUTER_WALL_BASE = 60
_REQUEST_TIMEOUT_MARGIN = 30


@dataclass
class LaunchPlan:
    """A typed, versioned, dry-run launch plan for a RepairProposal.

    Attributes:
        pipeline_id: Which pipeline this plan belongs to.
        command: The dry-run command line that *would* be launched (empty for a
            no-op plan). No process is actually launched here.
        cycles_out_append: The marker line to append to ``cycles.out`` on launch
            (empty for a no-op plan).
        endpoint_pin: The endpoint pin the pipeline runs on (verbatim).
        request_timeout: Per-request budget in seconds (>= outer_wall).
        outer_wall: Outer wall-clock budget in seconds.
        one_pipeline_per_endpoint: Invariant flag — always True (one pipeline per
            endpoint).
        rationale: Free-text rationale for the plan.
        version: The launch-plan schema version.
    """

    pipeline_id: str
    command: str
    cycles_out_append: str
    endpoint_pin: str
    request_timeout: int
    outer_wall: int
    one_pipeline_per_endpoint: bool
    rationale: str
    version: str = LAUNCH_PLAN_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "pipeline_id": self.pipeline_id,
            "command": self.command,
            "cycles_out_append": self.cycles_out_append,
            "endpoint_pin": self.endpoint_pin,
            "request_timeout": self.request_timeout,
            "outer_wall": self.outer_wall,
            "one_pipeline_per_endpoint": self.one_pipeline_per_endpoint,
            "rationale": self.rationale,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LaunchPlan:
        """Reconstruct a LaunchPlan from a dict produced by :meth:`to_dict`."""
        return cls(
            pipeline_id=data["pipeline_id"],
            command=data["command"],
            cycles_out_append=data["cycles_out_append"],
            endpoint_pin=data["endpoint_pin"],
            request_timeout=data["request_timeout"],
            outer_wall=data["outer_wall"],
            one_pipeline_per_endpoint=data["one_pipeline_per_endpoint"],
            rationale=data["rationale"],
            version=data["version"],
        )

    def validate(self) -> LaunchPlan:
        """Enforce the launch-plan invariants; return self or raise ValueError.

        Raises:
            ValueError: if any invariant is violated (see module docstring).
        """
        if not self.pipeline_id:
            raise ValueError(
                "launch plan invariant violated: pipeline_id must be non-empty"
            )
        if not self.version:
            raise ValueError(
                "launch plan invariant violated: version must be non-empty"
            )
        if not self.one_pipeline_per_endpoint:
            raise ValueError(
                "launch plan invariant violated: one_pipeline_per_endpoint "
                "must be True"
            )
        if self.outer_wall < 0:
            raise ValueError(
                "launch plan invariant violated: outer_wall must be >= 0"
            )
        if self.request_timeout < 0:
            raise ValueError(
                "launch plan invariant violated: request_timeout must be >= 0"
            )
        if self.request_timeout < self.outer_wall:
            raise ValueError(
                "launch plan invariant violated: request_timeout "
                f"({self.request_timeout}) must be >= outer_wall "
                f"({self.outer_wall})"
            )
        return self


def _reference_cycle(d: Diagnosis) -> int:
    """Deterministic cycle reference used to scale the wall-clock budgets.

    driver-death -> driver_death_cycle, wall-kill -> wall_kill_cycle, otherwise
    0 (a stall has no cycle number; the hung PID is not a cycle).
    """
    if d.driver_death_cycle is not None:
        return d.driver_death_cycle
    if d.wall_kill_cycle is not None:
        return d.wall_kill_cycle
    return 0


def build_launch_plan(proposal: RepairProposal) -> LaunchPlan:
    """Derive a deterministic, dry-run :class:`LaunchPlan` from a RepairProposal.

    Pure, deterministic, stdlib-only. No disk writes, no process launch. A healthy
    proposal (``failure_mode == "none"``) yields a no-op plan (empty command and
    marker, zero budgets). An actionable proposal yields a non-empty command and
    marker with budgets scaled by the reference cycle, always satisfying
    ``request_timeout >= outer_wall``.

    Args:
        proposal: The validated RepairProposal to derive a launch plan from.

    Returns:
        A validated LaunchPlan.
    """
    d = proposal.diagnosis

    if d.failure_mode == "none":
        plan = LaunchPlan(
            pipeline_id=proposal.pipeline_id,
            command="",
            cycles_out_append="",
            endpoint_pin=d.endpoint_pin,
            request_timeout=0,
            outer_wall=0,
            one_pipeline_per_endpoint=True,
            rationale="no-op (healthy); nothing to launch",
            version=LAUNCH_PLAN_VERSION,
        )
        plan.validate()
        return plan

    cycle = _reference_cycle(d)
    outer_wall = _OUTER_WALL_BASE + cycle
    request_timeout = outer_wall + _REQUEST_TIMEOUT_MARGIN
    command = (
        f"revolver launch --pipeline {proposal.pipeline_id} "
        f"--endpoint {d.endpoint_pin} --failure-mode {d.failure_mode}"
    )
    cycles_out_append = f"= LAUNCH {proposal.pipeline_id} {d.failure_mode} =\n"
    rationale = (
        f"dry-run launch plan for failure_mode={d.failure_mode!r}: "
        f"outer_wall={outer_wall}s request_timeout={request_timeout}s "
        f"(request_timeout >= outer_wall), one pipeline per endpoint."
    )
    plan = LaunchPlan(
        pipeline_id=proposal.pipeline_id,
        command=command,
        cycles_out_append=cycles_out_append,
        endpoint_pin=d.endpoint_pin,
        request_timeout=request_timeout,
        outer_wall=outer_wall,
        one_pipeline_per_endpoint=True,
        rationale=rationale,
        version=LAUNCH_PLAN_VERSION,
    )
    plan.validate()
    return plan
