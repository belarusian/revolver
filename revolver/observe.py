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

READ-ONLY invariants (TICKET-048): no process launch, no process kill, no write.
The only I/O is through the overridable seams (``read_cycles_out``); the default
seam does the real file read, but the logic is pure. Pure, deterministic,
stdlib-only.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
