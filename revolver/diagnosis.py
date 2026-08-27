"""revolver.diagnosis — parse a sentry check/rescue diagnosis into a typed record.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: the sentry check CLI (sentry/cli.py::_format_check_report) emits a stable
8-line dialect (driver / driver-death / wall-kill-no-merge / stall / live work /
cycles / gate-blocks / verdict). This module parses that dialect into a structured,
versioned ``Diagnosis`` dataclass. When sentry is not importable it degrades to
raw-artifact parsing (cycles.out markers, gate log cycle blocks, newest trajectory
outcome) and records ``source="raw-artifacts"`` so the provenance is never lost.

House exit-code convention (sentry): 0 = healthy, 1 = action needed, 2 = usage error.
Deterministic, stdlib-only, pure functions with overridable I/O seams (the sentry
pattern). Nothing here writes to disk or kills a process.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from revolver.sentry_client import SentryClient

# ---------------------------------------------------------------------------
# Allowed-value sets (used by validate())
# ---------------------------------------------------------------------------

_VALID_SOURCES = {"sentry-report", "raw-artifacts"}
_VALID_VERDICTS = {"HEALTHY", "ACTION NEEDED"}
_VALID_STALL_ACTIONS = {"none", "wait", "kill"}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Diagnosis:
    """A typed, versioned record of a pipeline failure diagnosis.

    Attributes:
        pipeline_id: Which pipeline this diagnosis belongs to (default "revolver").
        failure_mode: Coarse failure-mode tag (e.g. "driver-death", "wall-kill",
            "stall-kill", "none").
        evidence: Free-text evidence motivating the diagnosis.
        endpoint_pin: The endpoint pin the pipeline ran on (verbatim).
        driver_alive: Whether the driver process is alive.
        driver_death_cycle: Cycle number if driver-death detected, else None.
        wall_kill_cycle: Cycle number if wall-kill-no-merge detected, else None.
        stall_action: "none" | "wait" | "kill".
        stall_reason: Human-readable stall reason.
        live_work: Whether live work is present in the process tree.
        live_work_root: PID of the live-work root, if any.
        cycles_started: Cycle numbers that started.
        cycles_done: Cycle numbers that completed.
        cycles_in_flight: Cycle numbers currently in flight.
        cycles_wall_kill: Cycle numbers wall-killed.
        gate_blocks: Cycle numbers blocked at the gate.
        verdict: "HEALTHY" or "ACTION NEEDED".
        source: "sentry-report" | "raw-artifacts" — provenance.
        raw: The original text (for debugging).
        sentry_exit_code: The house exit code returned by sentry (0/1/2), if any.
    """

    pipeline_id: str = "revolver"
    failure_mode: str = "none"
    evidence: str = ""
    endpoint_pin: str = ""
    driver_alive: bool = True
    driver_death_cycle: int | None = None
    wall_kill_cycle: int | None = None
    stall_action: str = "none"
    stall_reason: str = ""
    live_work: bool = False
    live_work_root: int | None = None
    cycles_started: list[int] = field(default_factory=list)
    cycles_done: list[int] = field(default_factory=list)
    cycles_in_flight: list[int] = field(default_factory=list)
    cycles_wall_kill: list[int] = field(default_factory=list)
    gate_blocks: list[int] = field(default_factory=list)
    verdict: str = "HEALTHY"
    source: str = "sentry-report"
    raw: str = ""
    sentry_exit_code: int | None = None

    # -- derived properties -------------------------------------------------

    @property
    def action_needed(self) -> bool:
        """True when the diagnosis warrants a repair action."""
        return (
            self.driver_death_cycle is not None
            or self.wall_kill_cycle is not None
            or self.stall_action == "kill"
        )

    @property
    def exit_code(self) -> int:
        """House exit-code convention: 0=healthy, 1=action needed, 2=usage error."""
        if self.sentry_exit_code is not None:
            return self.sentry_exit_code
        return 1 if self.action_needed else 0

    # -- round-trip ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless for all fields)."""
        return {
            "pipeline_id": self.pipeline_id,
            "failure_mode": self.failure_mode,
            "evidence": self.evidence,
            "endpoint_pin": self.endpoint_pin,
            "driver_alive": self.driver_alive,
            "driver_death_cycle": self.driver_death_cycle,
            "wall_kill_cycle": self.wall_kill_cycle,
            "stall_action": self.stall_action,
            "stall_reason": self.stall_reason,
            "live_work": self.live_work,
            "live_work_root": self.live_work_root,
            "cycles_started": list(self.cycles_started),
            "cycles_done": list(self.cycles_done),
            "cycles_in_flight": list(self.cycles_in_flight),
            "cycles_wall_kill": list(self.cycles_wall_kill),
            "gate_blocks": list(self.gate_blocks),
            "verdict": self.verdict,
            "source": self.source,
            "raw": self.raw,
            "sentry_exit_code": self.sentry_exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Diagnosis:
        """Reconstruct a Diagnosis from a dict produced by :meth:`to_dict`."""
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    # -- validation ---------------------------------------------------------

    def validate(self) -> Diagnosis:
        """Validate the record's enum-like fields; return self or raise ValueError."""
        if self.source not in _VALID_SOURCES:
            raise ValueError(f"unknown source: {self.source!r}")
        if self.verdict not in _VALID_VERDICTS:
            raise ValueError(f"unknown verdict: {self.verdict!r}")
        if self.stall_action not in _VALID_STALL_ACTIONS:
            raise ValueError(f"unknown stall_action: {self.stall_action!r}")
        return self


# ---------------------------------------------------------------------------
# Parsing: sentry check report (stable 8-line dialect)
# ---------------------------------------------------------------------------

_RE_DRIVER = re.compile(r"^driver:\s+(alive|dead)\s*$")
_RE_DRIVER_DEATH = re.compile(r"^driver-death:\s+(DETECTED cycle (\d+)|none)\s*$")
_RE_WALL_KILL = re.compile(r"^wall-kill-no-merge:\s+(DETECTED cycle (\d+)|none)\s*$")
_RE_STALL = re.compile(r"^stall:\s+(\w+)\s+\((.+)\)\s*$")
_RE_LIVE_WORK = re.compile(r"^live work:\s+(yes \(root=(\d+)\)(?:\s*::.*)?|no)\s*$")
_RE_CYCLES = re.compile(
    r"^cycles:\s+started=\[(.*?)\]\s+done=\[(.*?)\]\s+in_flight=\[(.*?)\]\s+wall_kill=\[(.*?)\]\s*$"
)
_RE_GATE_BLOCKS = re.compile(r"^gate-blocks:\s+\[(.*?)\]\s*$")
_RE_VERDICT = re.compile(r"^verdict:\s+(ACTION NEEDED|HEALTHY)\s*$")


def _parse_int_list(s: str) -> list[int]:
    """Parse a comma-separated int list from a bracketed string."""
    s = s.strip()
    if not s:
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _derive_failure_mode(d: Diagnosis) -> str:
    """Derive a coarse failure-mode tag from the parsed fields."""
    if d.driver_death_cycle is not None:
        return "driver-death"
    if d.wall_kill_cycle is not None:
        return "wall-kill"
    if d.stall_action == "kill":
        return "stall-kill"
    return "none"


def parse_sentry_report(text: str) -> Diagnosis:
    """Parse a sentry check report (the stable 8-line dialect) into a Diagnosis.

    Pure function: no I/O. Deterministic.
    """
    d = Diagnosis(source="sentry-report", raw=text)
    for line in text.splitlines():
        line = line.strip()
        m = _RE_DRIVER.match(line)
        if m:
            d.driver_alive = m.group(1) == "alive"
            continue
        m = _RE_DRIVER_DEATH.match(line)
        if m:
            if m.group(2):
                d.driver_death_cycle = int(m.group(2))
            continue
        m = _RE_WALL_KILL.match(line)
        if m:
            if m.group(2):
                d.wall_kill_cycle = int(m.group(2))
            continue
        m = _RE_STALL.match(line)
        if m:
            d.stall_action = m.group(1)
            d.stall_reason = m.group(2)
            continue
        m = _RE_LIVE_WORK.match(line)
        if m:
            if m.group(1).startswith("yes"):
                d.live_work = True
                d.live_work_root = int(m.group(2))
            continue
        m = _RE_CYCLES.match(line)
        if m:
            d.cycles_started = _parse_int_list(m.group(1))
            d.cycles_done = _parse_int_list(m.group(2))
            d.cycles_in_flight = _parse_int_list(m.group(3))
            d.cycles_wall_kill = _parse_int_list(m.group(4))
            continue
        m = _RE_GATE_BLOCKS.match(line)
        if m:
            d.gate_blocks = _parse_int_list(m.group(1))
            continue
        m = _RE_VERDICT.match(line)
        if m:
            d.verdict = m.group(1)
            continue
    d.failure_mode = _derive_failure_mode(d)
    return d


# ---------------------------------------------------------------------------
# Parsing: raw artifacts (degraded mode when sentry is not installed)
# ---------------------------------------------------------------------------

# cycles.out marker grammar (tolerant, mirrors the sentry sentinel)
_PREFIX = r"(?:[A-Za-z0-9_-]+\s+)?"
_RE_DONE = re.compile(r"^=+\s*" + _PREFIX + r"CYCLE\s+(\d+)\s+done\b")
_RE_START = re.compile(r"^=+\s*" + _PREFIX + r"CYCLE\s+(\d+)\b")
# gate log cycle heading
_RE_GATE_CYCLE = re.compile(r"^##\s+Cycle\s+(\d+)\b")


def parse_raw_artifacts(
    cycles_out_text: str = "",
    gate_log_text: str = "",
    trajectory_outcome: str = "",
) -> Diagnosis:
    """Parse raw artifacts directly when sentry is not installed.

    Pure function: no I/O. Deterministic. Records ``source="raw-artifacts"``.
    """
    d = Diagnosis(source="raw-artifacts", raw=cycles_out_text[:500])

    # cycles.out markers
    started: set[int] = set()
    done: set[int] = set()
    for line in cycles_out_text.splitlines():
        line = line.strip()
        m = _RE_DONE.match(line)
        if m:
            n = int(m.group(1))
            started.add(n)
            done.add(n)
            continue
        m = _RE_START.match(line)
        if m:
            started.add(int(m.group(1)))

    d.cycles_started = sorted(started)
    d.cycles_done = sorted(done)
    d.cycles_in_flight = sorted(started - done)

    # gate log cycle headings -> gate blocks (cycles that have a heading)
    gate_blocks: set[int] = set()
    for line in gate_log_text.splitlines():
        m = _RE_GATE_CYCLE.match(line.strip())
        if m:
            gate_blocks.add(int(m.group(1)))
    d.gate_blocks = sorted(gate_blocks)

    # trajectory outcome -> evidence
    if trajectory_outcome:
        d.evidence = f"trajectory outcome: {trajectory_outcome}"

    # verdict: in-flight work means action needed
    d.verdict = "ACTION NEEDED" if d.cycles_in_flight else "HEALTHY"
    d.failure_mode = _derive_failure_mode(d)
    return d


# ---------------------------------------------------------------------------
# High-level entry point (with I/O seam)
# ---------------------------------------------------------------------------


def diagnose(
    project_dir: str | Path,
    *,
    read_file: Callable[[Path], str] | None = None,
    sentry_available: bool | None = None,
    client: SentryClient | None = None,
) -> Diagnosis:
    """Diagnose a project directory.

    Tries sentry first (if importable); falls back to raw-artifact parsing and
    records the provenance.

    Args:
        project_dir: Path to the project directory (containing cycles.out, ai/).
        read_file: Overridable I/O seam (defaults to ``Path.read_text``).
        sentry_available: Override for sentry importability (for testing).
        client: Optional :class:`SentryClient` for the sentry path (defaults to a
            fresh client; injectable so tests never shell out).

    Returns:
        A validated ``Diagnosis`` dataclass.
    """
    project_dir = Path(project_dir)
    if read_file is None:
        read_file = lambda p: p.read_text()

    if sentry_available is None:
        try:
            import sentry  # noqa: F401

            sentry_available = True
        except ImportError:
            sentry_available = False

    note = ""
    if sentry_available:
        try:
            from revolver.sentry_client import diagnose_via_sentry

            return diagnose_via_sentry(project_dir, client=client, read_file=read_file)
        except ImportError:
            note = "sentry unavailable (not importable); fell back to raw artifacts"
        except (OSError, ValueError, RuntimeError) as exc:
            note = f"sentry runner failed ({exc.__class__.__name__}); fell back to raw artifacts"
    else:
        note = "sentry unavailable (not importable); fell back to raw artifacts"

    cycles_out_path = project_dir / "cycles.out"
    ai_dir = project_dir / "ai"

    cycles_out_text = ""
    if cycles_out_path.exists():
        cycles_out_text = read_file(cycles_out_path)

    gate_log_text = ""
    gate_log_path = ai_dir / "cycle-001-revolver-gate.md"
    if gate_log_path.exists():
        gate_log_text = read_file(gate_log_path)

    trajectory_outcome = ""
    traj_dir = ai_dir / "trajectories"
    if traj_dir.exists():
        traj_files = sorted(traj_dir.glob("*.json"))
        if traj_files:
            try:
                data = json.loads(read_file(traj_files[-1]))
                trajectory_outcome = str(data.get("outcome", ""))
            except (json.JSONDecodeError, OSError):
                pass

    d = parse_raw_artifacts(
        cycles_out_text=cycles_out_text,
        gate_log_text=gate_log_text,
        trajectory_outcome=trajectory_outcome,
    )
    d.evidence = (d.evidence + "; " if d.evidence else "") + note
    return d
