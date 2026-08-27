"""revolver.observe — the read-only observer half of the repair loop.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: cycles 8-9 landed deploy + relaunch (the launch/execute half of the
loop). Cycle 10 begins the observe + report phase (Build Order cycles 10-12).
JUNIOR.md §8 "Done" = the ``========== CYCLE N done ==========` marker in
``cycles.out``; a bare ``========== CYCLE N ==========` (no "done") is a
started/in-flight marker. JUNIOR.md §1: "the gate log ... append-only ground
truth — position is the only order; never reorder, never rewrite". This module
parses ``cycles.out`` into per-cycle markers in FILE ORDER (never reordered,
never deduped — a cycle may appear more than once across restarts) and reports,
for the cycles the driver is responsible for, which are done, which are
in-flight, and which are *gaps* — reported honestly, never assumed done.

The §7 scar (JUNIOR.md): a continuation launch reused a filename with ``>`` and
truncated prior cycle markers, so a run NO-GO'd on a gap that was an operator
typo, not a real miss. The rule it motivates: "the observer can only union what
the launch preserved" and must report honestly when markers are truly absent.
A cycle with no marker is a gap; the observer never assumes it is done.

Cycle 11 extends the observer with the trajectory half and the recurrence
verdict. JUNIOR.md §1: the outer reads each cycle's JSON trajectory
(``{outcome, messages}``); the outcome dialect is ``exit:task_complete`` /
``max_steps_reached`` / ``error`` (run.py step 2). ``parse_trajectory_outcomes``
parses that JSON (a single object or an array of objects) into per-cycle
outcomes in FILE ORDER (never reordered, never deduped). ``report`` composes the
Cycle 10 marker observation with the trajectory outcomes and the diagnosed
``failure_mode`` into a recurrence verdict: the diagnosed failure mode has
recurred when the observed run shows a non-complete trajectory outcome, a gap
where a done marker was expected, or an in-flight cycle; it is clean when all
expected cycles are done and every outcome is complete.

READ-ONLY invariants (TICKET-048): no process launch, no process kill, no write.
The only I/O is through the overridable seams (``read_cycles_out``,
``read_trajectory``); the default seams do the real file reads, but the logic is
pure. Pure, deterministic, stdlib-only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from revolver.diagnosis import Diagnosis

# ---------------------------------------------------------------------------
# Marker grammar (mirrors the §8 sentinel; tolerant, position-preserving)
# ---------------------------------------------------------------------------

# The §8 "Done" marker: ``========== CYCLE N done ==========`. This is the
# default ``done_pattern`` seam; a cycle is *done* only on this marker.
_DEFAULT_DONE_PATTERN = re.compile(r"^=+\s*CYCLE\s+(\d+)\s+done\b")

# A bare start marker: ``========== CYCLE N ==========` (no "done"). A line that
# matches this but not the done pattern is *started* (in-flight). Checked only
# after the done pattern, so a done line is never misread as started.
_START_PATTERN = re.compile(r"^=+\s*CYCLE\s+(\d+)\b")


# ---------------------------------------------------------------------------
# CycleMarker
# ---------------------------------------------------------------------------


@dataclass
class CycleMarker:
    """One parsed marker line from ``cycles.out``.

    Attributes:
        cycle: The cycle number the marker refers to.
        status: ``"done"`` (the §8 done marker) or ``"started"`` (a bare start
            marker, in-flight).
        raw: The original line the marker was parsed from (provenance).
    """

    cycle: int
    status: str
    raw: str


# ---------------------------------------------------------------------------
# parse_cycle_markers
# ---------------------------------------------------------------------------


def parse_cycle_markers(
    text: str,
    *,
    done_pattern: re.Pattern[str] | None = None,
) -> list[CycleMarker]:
    """Parse ``cycles.out`` text into per-cycle markers, in FILE ORDER.

    Scans ``text`` line by line. A line matching the done pattern yields
    ``CycleMarker(n, "done", line)``; a line matching the bare start pattern
    (and not the done pattern) yields ``CycleMarker(n, "started", line)``.
    Markers are returned in the order they appear in the file — position is the
    only order. They are NEVER reordered and NEVER deduped by cycle number (a
    cycle may appear more than once across restarts).

    Args:
        text: The ``cycles.out`` text to parse.
        done_pattern: Overridable seam — a compiled regex with one capture group
            (the cycle number) that matches a *done* marker. Defaults to the §8
            done-marker regex. Inject a custom dialect to override what counts
            as "done".

    Returns:
        A list of :class:`CycleMarker` in file order. Empty text -> empty list.

    Pure, deterministic, stdlib-only; no I/O.
    """
    if done_pattern is None:
        done_pattern = _DEFAULT_DONE_PATTERN

    markers: list[CycleMarker] = []
    for line in text.splitlines():
        stripped = line.strip()
        m = done_pattern.match(stripped)
        if m:
            markers.append(CycleMarker(cycle=int(m.group(1)), status="done", raw=line))
            continue
        m = _START_PATTERN.match(stripped)
        if m:
            markers.append(CycleMarker(cycle=int(m.group(1)), status="started", raw=line))
    return markers


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------


@dataclass
class Observation:
    """A read-only observation of the cycles the driver is responsible for.

    Each list is a subset of the input ``cycles`` (in the input's order). The
    four lists partition the input: every cycle is in exactly one of
    ``cycles_done``, ``cycles_in_flight``, or ``gaps``; ``cycles_seen`` is the
    union of the first two.

    Attributes:
        cycles_seen: Cycles with any marker (done or started).
        cycles_done: Cycles with a done marker.
        cycles_in_flight: Cycles with a started marker but no done marker.
        gaps: Cycles with NO marker at all — reported honestly, never assumed
            done.
        note: A deterministic, human-readable summary.
    """

    cycles_seen: list[int] = field(default_factory=list)
    cycles_done: list[int] = field(default_factory=list)
    cycles_in_flight: list[int] = field(default_factory=list)
    gaps: list[int] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "cycles_seen": list(self.cycles_seen),
            "cycles_done": list(self.cycles_done),
            "cycles_in_flight": list(self.cycles_in_flight),
            "gaps": list(self.gaps),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Observation:
        """Reconstruct an Observation from a dict produced by :meth:`to_dict`."""
        return cls(
            cycles_seen=list(data["cycles_seen"]),
            cycles_done=list(data["cycles_done"]),
            cycles_in_flight=list(data["cycles_in_flight"]),
            gaps=list(data["gaps"]),
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# Default seams
# ---------------------------------------------------------------------------


def _default_read_cycles_out() -> str:
    """Default ``read_cycles_out`` seam: read the real ``cycles.out`` file.

    Returns an empty string when the file is absent (the observer then reports
    every cycle as a gap — honestly, never assumed done).
    """
    path = Path("cycles.out")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# observe
# ---------------------------------------------------------------------------


def _build_note(
    total: int,
    cycles_done: list[int],
    cycles_in_flight: list[int],
    gaps: list[int],
) -> str:
    """Build a deterministic, human-readable summary of an observation."""
    if total == 0:
        return "no cycles to observe"
    parts = [f"{len(cycles_done)}/{total} done"]
    if cycles_in_flight:
        parts.append(f"{len(cycles_in_flight)} in flight")
    if gaps:
        parts.append(f"{len(gaps)} gaps (no marker; not assumed done)")
    return "; ".join(parts)


def observe(
    cycles: Sequence[int],
    *,
    markers: Sequence[CycleMarker] | None = None,
    read_cycles_out: Callable[[], str] | None = None,
) -> Observation:
    """Observe which of ``cycles`` are done, in-flight, or gaps.

    Given the ordered list of cycle numbers the driver is responsible for and
    the parsed markers, report which are done, which are in-flight, and which
    are *gaps* — reported honestly. A cycle with no marker is a gap; the
    observer never assumes it is done (the §7 union rule).

    Args:
        cycles: Ordered list of cycle numbers the driver is responsible for.
        markers: Overridable seam — a list of :class:`CycleMarker`. When ``None``
            (the default), the markers are parsed from the text returned by
            ``read_cycles_out``.
        read_cycles_out: Overridable seam that returns the text content of
            ``cycles.out``. Defaults to reading the real file. Only consulted
            when ``markers`` is ``None``.

    Returns:
        An :class:`Observation`. The four lists partition ``cycles`` (in the
        input's order): every cycle is in exactly one of ``cycles_done``,
        ``cycles_in_flight``, or ``gaps``; ``cycles_seen`` is the union of the
        first two.

    READ-ONLY: the only I/O is through the seams; no process launch, no kill, no
    write.
    """
    if markers is None:
        if read_cycles_out is None:
            read_cycles_out = _default_read_cycles_out
        markers = parse_cycle_markers(read_cycles_out())

    done: set[int] = set()
    started: set[int] = set()
    for m in markers:
        if m.status == "done":
            done.add(m.cycle)
        elif m.status == "started":
            started.add(m.cycle)

    cycles_list = list(cycles)
    cycles_done = [c for c in cycles_list if c in done]
    cycles_in_flight = [c for c in cycles_list if c in started and c not in done]
    cycles_seen = [c for c in cycles_list if c in done or c in started]
    gaps = [c for c in cycles_list if c not in done and c not in started]

    return Observation(
        cycles_seen=cycles_seen,
        cycles_done=cycles_done,
        cycles_in_flight=cycles_in_flight,
        gaps=gaps,
        note=_build_note(len(cycles_list), cycles_done, cycles_in_flight, gaps),
    )


# ---------------------------------------------------------------------------
# Trajectory outcome dialect (JUNIOR.md §1 / run.py step 2)
# ---------------------------------------------------------------------------

# The §1 trajectory outcome dialect. A trajectory is the ``{outcome, messages}``
# object the outer reads after each cycle (run.py step 2: "inspect its 'outcome'
# (exit:task_complete / max_steps_reached / error)"). ``exit:task_complete`` is the
# only *complete* outcome; ``max_steps_reached`` and ``error`` (and any other value)
# are *non-complete* — the inner stopped without finishing the chunk.
_COMPLETE_OUTCOME = "exit:task_complete"


def _is_complete_outcome(outcome: str) -> bool:
    """True when a trajectory outcome is the complete (task-finished) one.

    Only ``exit:task_complete`` counts as complete. ``max_steps_reached``,
    ``error``, and any other value are non-complete.
    """
    return outcome == _COMPLETE_OUTCOME


# ---------------------------------------------------------------------------
# TrajectoryOutcome
# ---------------------------------------------------------------------------


@dataclass
class TrajectoryOutcome:
    """One parsed per-cycle trajectory outcome.

    Attributes:
        cycle: The cycle number the trajectory belongs to. When the trajectory
            JSON carries no explicit cycle number (the §1 dialect has none), this
            is the 1-based position of the object in the array (or 1 for a single
            object) — file order is the only order.
        outcome: The raw ``outcome`` string (e.g. ``"exit:task_complete"``,
            ``"max_steps_reached"``, ``"error"``). Completeness is derived, not
            stored: see :func:`_is_complete_outcome`.
        raw: The original JSON text the outcome was parsed from (provenance).
    """

    cycle: int
    outcome: str
    raw: str


# ---------------------------------------------------------------------------
# parse_trajectory_outcomes
# ---------------------------------------------------------------------------


def _extract_outcome(obj: Any) -> str:
    """Pull the ``outcome`` string out of one trajectory object (defensive)."""
    if isinstance(obj, dict):
        return str(obj.get("outcome", ""))
    return ""


def parse_trajectory_outcomes(
    text: str,
    *,
    read_trajectory: Callable[[], str] | None = None,
) -> list[TrajectoryOutcome]:
    """Parse the outer's per-cycle trajectory JSON into per-cycle outcomes.

    The §1 dialect is a ``{outcome, messages}`` object, or a JSON array of such
    objects (one per cycle). This parses either shape into a list of
    :class:`TrajectoryOutcome` in FILE ORDER — the array's order is preserved and
    never reordered or deduped (position is the only order, JUNIOR.md §1).

    Args:
        text: The trajectory JSON text to parse. A single ``{outcome, messages}``
            object, or a JSON array of such objects.
        read_trajectory: Overridable seam. When ``text`` is empty (``""``) and a
            ``read_trajectory`` is supplied, the text is taken from the seam
            instead (the default seam reads the newest trajectory file). This lets
            tests inject a fake without touching the filesystem.

    Returns:
        A list of :class:`TrajectoryOutcome` in file order. Malformed JSON, an
        empty string, or a non-object/non-array payload -> empty list (never
        raises).

    Pure, deterministic, stdlib-only; the only I/O is through ``read_trajectory``.
    """
    if not text:
        if read_trajectory is None:
            read_trajectory = _default_read_trajectory
        text = read_trajectory()
    if not text:
        return []

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []

    # Normalize to a list of objects, preserving file order.
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [data]
    else:
        return []

    outcomes: list[TrajectoryOutcome] = []
    for idx, obj in enumerate(items, start=1):
        outcome = _extract_outcome(obj)
        outcomes.append(
            TrajectoryOutcome(
                cycle=idx,
                outcome=outcome,
                raw=text,
            )
        )
    return outcomes


# ---------------------------------------------------------------------------
# Default trajectory seam
# ---------------------------------------------------------------------------


def _default_read_trajectory() -> str:
    """Default ``read_trajectory`` seam: read the newest trajectory file.

    Looks for the newest ``*.json`` in ``ai/trajectories`` (the canonical
    artifact dir, JUNIOR.md §7), falling back to ``trajectories`` at the project
    root. Returns an empty string when no trajectory file exists (the parser then
    yields an empty list — honestly, never assumed complete).
    """
    for candidate in (Path("ai") / "trajectories", Path("trajectories")):
        if candidate.is_dir():
            files = sorted(candidate.glob("*.json"))
            if files:
                return files[-1].read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# RecurrenceReport
# ---------------------------------------------------------------------------


@dataclass
class RecurrenceReport:
    """A read-only recurrence verdict for a diagnosed failure mode.

    Composes the Cycle 10 marker observation (done / in-flight / gaps) with the
    trajectory outcomes and the diagnosed ``failure_mode`` into a single verdict:
    did the diagnosed failure mode recur in the observed run?

    Attributes:
        failure_mode: The diagnosed failure mode under test (from the
            :class:`~revolver.diagnosis.Diagnosis`), verbatim.
        recurred: True when the observed run shows the diagnosed failure mode
            recurring — a non-complete trajectory outcome (``max_steps_reached`` /
            ``error``), a gap where a done marker was expected, or an in-flight
            cycle. False when the run is clean (all expected cycles done and every
            outcome complete).
        cycles_done: Cycles with a done marker (from the observation).
        cycles_in_flight: Cycles started but not done (from the observation).
        gaps: Cycles with no marker at all — reported honestly, never assumed done.
        outcomes: The parsed per-cycle :class:`TrajectoryOutcome` list (file order).
        note: A deterministic, human-readable summary of the verdict.
    """

    failure_mode: str
    recurred: bool
    cycles_done: list[int] = field(default_factory=list)
    cycles_in_flight: list[int] = field(default_factory=list)
    gaps: list[int] = field(default_factory=list)
    outcomes: list[TrajectoryOutcome] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "failure_mode": self.failure_mode,
            "recurred": self.recurred,
            "cycles_done": list(self.cycles_done),
            "cycles_in_flight": list(self.cycles_in_flight),
            "gaps": list(self.gaps),
            "outcomes": [
                {
                    "cycle": o.cycle,
                    "outcome": o.outcome,
                    "raw": o.raw,
                }
                for o in self.outcomes
            ],
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecurrenceReport:
        """Reconstruct a RecurrenceReport from a dict produced by :meth:`to_dict`."""
        outcomes = [
            TrajectoryOutcome(
                cycle=o["cycle"],
                outcome=o["outcome"],
                raw=o["raw"],
            )
            for o in data.get("outcomes", [])
        ]
        return cls(
            failure_mode=data["failure_mode"],
            recurred=data["recurred"],
            cycles_done=list(data["cycles_done"]),
            cycles_in_flight=list(data["cycles_in_flight"]),
            gaps=list(data["gaps"]),
            outcomes=outcomes,
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def _build_recurrence_note(
    failure_mode: str,
    recurred: bool,
    cycles_done: list[int],
    cycles_in_flight: list[int],
    gaps: list[int],
    outcomes: list[TrajectoryOutcome],
) -> str:
    """Build a deterministic, human-readable summary of a recurrence verdict."""
    parts = [f"failure_mode={failure_mode}"]
    parts.append(f"{len(cycles_done)} done")
    if cycles_in_flight:
        parts.append(f"{len(cycles_in_flight)} in flight")
    if gaps:
        parts.append(f"{len(gaps)} gaps (no marker; not assumed done)")
    non_complete = [o for o in outcomes if not _is_complete_outcome(o.outcome)]
    if non_complete:
        parts.append(f"{len(non_complete)} non-complete outcome(s)")
    parts.append("RECURRED" if recurred else "clean")
    return "; ".join(parts)


def report(
    diagnosis: Diagnosis,
    *,
    markers: Sequence[CycleMarker] | None = None,
    read_cycles_out: Callable[[], str] | None = None,
    read_trajectory: Callable[[], str] | None = None,
) -> RecurrenceReport:
    """Compose the marker observation + trajectory outcomes into a recurrence verdict.

    Takes a :class:`~revolver.diagnosis.Diagnosis` (which carries the diagnosed
    ``failure_mode`` and the ordered cycle numbers the driver is responsible for)
    and reports whether that failure mode recurred in the observed run.

    The verdict is ``recurred=True`` when the observed run shows the diagnosed
    failure mode recurring, i.e. ANY of:

    * a non-complete trajectory outcome (``max_steps_reached`` / ``error`` / any
      value other than ``exit:task_complete``);
    * a gap — a cycle with no marker at all where a done marker was expected
      (reported honestly, never assumed done, the §7 union rule);
    * an in-flight cycle — started but not done.

    It is ``recurred=False`` (clean) only when every expected cycle is done AND
    every trajectory outcome is complete.

    Args:
        diagnosis: The diagnosed record. Its ``failure_mode`` is reported
            verbatim; the ordered set of cycles the driver is responsible for is
            the union of its ``cycles_started`` / ``cycles_done`` /
            ``cycles_in_flight`` (first-seen order).
        markers: Overridable seam — a list of :class:`CycleMarker`. When ``None``
            (the default), the markers are parsed from the text returned by
            ``read_cycles_out``.
        read_cycles_out: Overridable seam returning the ``cycles.out`` text.
            Defaults to reading the real file. Only consulted when ``markers`` is
            ``None``.
        read_trajectory: Overridable seam returning the trajectory JSON text.
            Defaults to reading the newest trajectory file. Inject a fake so tests
            never touch the filesystem.

    Returns:
        A :class:`RecurrenceReport`.

    READ-ONLY: the only I/O is through the seams; no process launch, no kill, no
    write. Pure, deterministic, stdlib-only.
    """
    # The ordered cycles the driver is responsible for: the union of the
    # diagnosis's cycle sets, in first-seen order (started, then done, then
    # in-flight). A cycle is *expected* if it appears in any of them.
    cycles: list[int] = []
    for c in (
        list(diagnosis.cycles_started)
        + list(diagnosis.cycles_done)
        + list(diagnosis.cycles_in_flight)
    ):
        if c not in cycles:
            cycles.append(c)

    obs = observe(cycles, markers=markers, read_cycles_out=read_cycles_out)

    if read_trajectory is None:
        read_trajectory = _default_read_trajectory
    outcomes = parse_trajectory_outcomes("", read_trajectory=read_trajectory)

    non_complete = [o for o in outcomes if not _is_complete_outcome(o.outcome)]
    recurred = bool(obs.gaps) or bool(obs.cycles_in_flight) or bool(non_complete)

    return RecurrenceReport(
        failure_mode=diagnosis.failure_mode,
        recurred=recurred,
        cycles_done=obs.cycles_done,
        cycles_in_flight=obs.cycles_in_flight,
        gaps=obs.gaps,
        outcomes=outcomes,
        note=_build_recurrence_note(
            diagnosis.failure_mode,
            recurred,
            obs.cycles_done,
            obs.cycles_in_flight,
            obs.gaps,
            outcomes,
        ),
    )
