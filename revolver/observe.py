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

Cycle 12 completes the observe + report phase with the git merge-commit half of
the §8 "Done" definition and the final report. JUNIOR.md §8: "Done" = the
``========== CYCLE N done ==========` marker in ``cycles.out`` AND no driver
process AND the expected merge commits on main. The done-marker half is Cycle 10
(``observe``); the no-driver-process half is ``relaunch.verify_relaunch`` (the
``driver_alive`` seam); the merge-commit half is this cycle.
``parse_merge_commits`` parses the git log text into per-cycle merge commits in
FILE ORDER (never reordered, never deduped — a cycle may have more than one merge
across restarts); ``observe_git`` reports which expected cycles have the expected
merge commit and which are *missing* (reported honestly, never assumed merged, the
§7 union rule); ``render_final_report`` composes the Cycle 10 marker observation,
the Cycle 11 trajectory outcomes + recurrence verdict (reused, NOT re-derived),
and the Cycle 12 git observation into a single :class:`FinalReport`; ``render``
renders that report as deterministic, human-readable text.

READ-ONLY invariants (TICKET-048): no process launch, no process kill, no write.
The only I/O is through the overridable seams (``read_cycles_out``,
``read_trajectory``, ``read_git_log``); the default seams do the real file reads,
but the logic is pure. Pure, deterministic, stdlib-only.
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


def _expected_cycles(diagnosis: Diagnosis) -> list[int]:
    """The ordered cycles the driver is responsible for (first-seen order).

    The union of the diagnosis's ``cycles_started`` / ``cycles_done`` /
    ``cycles_in_flight`` in first-seen order (started, then done, then
    in-flight). A cycle is *expected* if it appears in any of them. Shared by
    :func:`report` (Cycle 11) and :func:`render_final_report` (Cycle 12) so the
    expected-cycle derivation lives in exactly one place.
    """
    cycles: list[int] = []
    for c in (
        list(diagnosis.cycles_started)
        + list(diagnosis.cycles_done)
        + list(diagnosis.cycles_in_flight)
    ):
        if c not in cycles:
            cycles.append(c)
    return cycles


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
    cycles = _expected_cycles(diagnosis)

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


# ---------------------------------------------------------------------------
# Git merge-commit dialect (JUNIOR.md §8 "Done" merge-commit half)
# ---------------------------------------------------------------------------

# The §8 "Done" merge-commit half: the expected merge commits on main. The repo's
# convention is a merge-commit line naming the build cycle in its branch name:
# ``Merge pull request #N from <owner>/build<cycle>/...``. The default
# ``merge_pattern`` seam captures the cycle number from the branch name (one
# capture group). A cycle may have more than one merge across restarts, so the
# parser never dedupes by cycle number — position is the only order.
_DEFAULT_MERGE_PATTERN = re.compile(r"build(\d+)/")


# ---------------------------------------------------------------------------
# MergeCommit
# ---------------------------------------------------------------------------


@dataclass
class MergeCommit:
    """One parsed merge-commit line from the git log.

    Attributes:
        cycle: The build cycle number the merge commit belongs to (captured from
            the branch name, e.g. ``build12/...``).
        sha: The commit hash the line names (the leading token of the line); the
            empty string when the line carries no leading sha token.
        raw: The original line the merge commit was parsed from (provenance).
    """

    cycle: int
    sha: str
    raw: str


# ---------------------------------------------------------------------------
# parse_merge_commits
# ---------------------------------------------------------------------------


def _leading_sha(line: str) -> str:
    """Return the leading sha token of a git log line, or ``""`` if none.

    A git log line of the form ``<sha> <subject>`` carries the commit hash as
    its first whitespace-delimited token. A token counts as a sha only when it
    is a plausible commit hash (hex, 7-40 chars); a bare subject line (no
    leading sha) yields the empty string.
    """
    parts = line.split()
    if not parts:
        return ""
    token = parts[0]
    if 7 <= len(token) <= 40 and all(c in "0123456789abcdefABCDEF" for c in token):
        return token
    return ""


def parse_merge_commits(
    text: str,
    *,
    merge_pattern: re.Pattern[str] | None = None,
) -> list[MergeCommit]:
    """Parse git log text into per-cycle merge commits, in FILE ORDER.

    Scans ``text`` line by line. A line matching ``merge_pattern`` yields
    ``MergeCommit(cycle=int(group1), sha=<leading sha>, raw=<line>)``. Commits
    are returned in the order they appear in the file — position is the only
    order. They are NEVER reordered and NEVER deduped by cycle number (a cycle
    may have more than one merge across restarts).

    Args:
        text: The git log text to parse (e.g. ``git log --oneline`` output).
        merge_pattern: Overridable seam — a compiled regex with one capture group
            (the cycle number) that matches a merge-commit line naming the cycle.
            Defaults to the repo's ``build<cycle>/`` branch-name convention.

    Returns:
        A list of :class:`MergeCommit` in file order. Empty text / no match ->
        empty list.

    Pure, deterministic, stdlib-only; no I/O.
    """
    if merge_pattern is None:
        merge_pattern = _DEFAULT_MERGE_PATTERN

    commits: list[MergeCommit] = []
    for line in text.splitlines():
        m = merge_pattern.search(line)
        if m:
            commits.append(
                MergeCommit(
                    cycle=int(m.group(1)),
                    sha=_leading_sha(line),
                    raw=line,
                )
            )
    return commits


# ---------------------------------------------------------------------------
# GitObservation
# ---------------------------------------------------------------------------


@dataclass
class GitObservation:
    """A read-only observation of the expected merge commits on main.

    The two lists partition the input ``cycles`` (in the input's order): every
    cycle is in exactly one of ``cycles_merged`` or ``cycles_missing``.

    Attributes:
        cycles_merged: Cycles that have the expected merge commit.
        cycles_missing: Cycles with NO merge commit — reported honestly, never
            assumed merged (the §7 union rule).
        note: A deterministic, human-readable summary.
    """

    cycles_merged: list[int] = field(default_factory=list)
    cycles_missing: list[int] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "cycles_merged": list(self.cycles_merged),
            "cycles_missing": list(self.cycles_missing),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GitObservation:
        """Reconstruct a GitObservation from a dict produced by :meth:`to_dict`."""
        return cls(
            cycles_merged=list(data["cycles_merged"]),
            cycles_missing=list(data["cycles_missing"]),
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# Default git-log seam
# ---------------------------------------------------------------------------


def _default_read_git_log() -> str:
    """Default ``read_git_log`` seam: read the real git log (read-only).

    Reads the ``.git/logs/HEAD`` reflog (a plain file read — no process launch,
    no kill, no write) and returns the lines that name a merge commit, in file
    order. Returns an empty string when the reflog is absent (the observer then
    reports every cycle as missing — honestly, never assumed merged).
    """
    path = Path(".git") / "logs" / "HEAD"
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if "Merge pull request" in line)


# ---------------------------------------------------------------------------
# observe_git
# ---------------------------------------------------------------------------


def _build_git_note(
    total: int,
    cycles_merged: list[int],
    cycles_missing: list[int],
) -> str:
    """Build a deterministic, human-readable summary of a git observation."""
    if total == 0:
        return "no cycles to observe"
    parts = [f"{len(cycles_merged)}/{total} merged"]
    if cycles_missing:
        parts.append(f"{len(cycles_missing)} missing (no merge commit; not assumed merged)")
    return "; ".join(parts)


def observe_git(
    cycles: Sequence[int],
    *,
    merge_commits: Sequence[MergeCommit] | None = None,
    read_git_log: Callable[[], str] | None = None,
) -> GitObservation:
    """Observe which of ``cycles`` have the expected merge commit.

    Given the ordered list of cycle numbers the driver is responsible for and
    the parsed merge commits, report which are merged and which are *missing* —
    reported honestly. A cycle with no merge commit is missing; the observer
    never assumes it is merged (the §7 union rule).

    Args:
        cycles: Ordered list of cycle numbers the driver is responsible for.
        merge_commits: Overridable seam — a list of :class:`MergeCommit`. When
            ``None`` (the default), the commits are parsed from the text returned
            by ``read_git_log``.
        read_git_log: Overridable seam that returns the git log text. Defaults to
            reading the real reflog. Only consulted when ``merge_commits`` is
            ``None``.

    Returns:
        A :class:`GitObservation`. The two lists partition ``cycles`` (in the
        input's order): every cycle is in exactly one of ``cycles_merged`` or
        ``cycles_missing``.

    READ-ONLY: the only I/O is through the seams; no process launch, no kill, no
    write. Pure, deterministic, stdlib-only.
    """
    if merge_commits is None:
        if read_git_log is None:
            read_git_log = _default_read_git_log
        merge_commits = parse_merge_commits(read_git_log())

    merged: set[int] = {c.cycle for c in merge_commits}
    cycles_list = list(cycles)
    cycles_merged = [c for c in cycles_list if c in merged]
    cycles_missing = [c for c in cycles_list if c not in merged]

    return GitObservation(
        cycles_merged=cycles_merged,
        cycles_missing=cycles_missing,
        note=_build_git_note(len(cycles_list), cycles_merged, cycles_missing),
    )


# ---------------------------------------------------------------------------
# FinalReport
# ---------------------------------------------------------------------------


@dataclass
class FinalReport:
    """A read-only final report: did the diagnosed failure mode recur?

    Composes the Cycle 10 marker observation, the Cycle 11 trajectory outcomes +
    recurrence verdict, and the Cycle 12 git observation into a single report.

    Attributes:
        failure_mode: The diagnosed failure mode under test (verbatim).
        recurred: The Cycle 11 recurrence verdict (reused, NOT re-derived).
        observation: The Cycle 10 marker :class:`Observation`.
        outcomes: The Cycle 11 parsed per-cycle :class:`TrajectoryOutcome` list
            (file order).
        git: The Cycle 12 :class:`GitObservation`.
        note: A deterministic, human-readable summary of the verdict.
    """

    failure_mode: str
    recurred: bool
    observation: Observation = field(default_factory=Observation)
    outcomes: list[TrajectoryOutcome] = field(default_factory=list)
    git: GitObservation = field(default_factory=GitObservation)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "failure_mode": self.failure_mode,
            "recurred": self.recurred,
            "observation": self.observation.to_dict(),
            "outcomes": [
                {
                    "cycle": o.cycle,
                    "outcome": o.outcome,
                    "raw": o.raw,
                }
                for o in self.outcomes
            ],
            "git": self.git.to_dict(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinalReport:
        """Reconstruct a FinalReport from a dict produced by :meth:`to_dict`."""
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
            observation=Observation.from_dict(data["observation"]),
            outcomes=outcomes,
            git=GitObservation.from_dict(data["git"]),
            note=data["note"],
        )


# ---------------------------------------------------------------------------
# render_final_report
# ---------------------------------------------------------------------------


def _build_final_note(
    failure_mode: str,
    recurred: bool,
    observation: Observation,
    git: GitObservation,
) -> str:
    """Build a deterministic, human-readable summary of a final report."""
    parts = [f"failure_mode={failure_mode}"]
    parts.append(f"{len(observation.cycles_done)} done")
    if observation.cycles_in_flight:
        parts.append(f"{len(observation.cycles_in_flight)} in flight")
    if observation.gaps:
        parts.append(f"{len(observation.gaps)} gaps (no marker; not assumed done)")
    parts.append(f"{len(git.cycles_merged)} merged")
    if git.cycles_missing:
        parts.append(f"{len(git.cycles_missing)} missing (no merge commit; not assumed merged)")
    parts.append("RECURRED" if recurred else "clean")
    return "; ".join(parts)


def render_final_report(
    diagnosis: Diagnosis,
    *,
    markers: Sequence[CycleMarker] | None = None,
    read_cycles_out: Callable[[], str] | None = None,
    read_trajectory: Callable[[], str] | None = None,
    merge_commits: Sequence[MergeCommit] | None = None,
    read_git_log: Callable[[], str] | None = None,
) -> FinalReport:
    """Compose the marker + trajectory + git observations into a final report.

    Takes a :class:`~revolver.diagnosis.Diagnosis` and composes the Cycle 10
    marker observation (:func:`observe`), the Cycle 11 trajectory outcomes +
    recurrence verdict (:func:`report`), and the Cycle 12 git observation
    (:func:`observe_git`) into a single :class:`FinalReport`.

    The report is a pure composition, NOT a re-derivation: ``recurred`` is the
    Cycle 11 recurrence verdict (reused, not re-derived) and the diagnosed
    ``failure_mode`` is reported verbatim. The expected cycles are the union of
    the diagnosis's ``cycles_started`` / ``cycles_done`` / ``cycles_in_flight``
    (first-seen order) — the same derivation :func:`report` uses.

    Args:
        diagnosis: The diagnosed record. Its ``failure_mode`` is reported
            verbatim.
        markers: Overridable seam — a list of :class:`CycleMarker`. When ``None``
            (the default), the markers are parsed from the text returned by
            ``read_cycles_out``.
        read_cycles_out: Overridable seam returning the ``cycles.out`` text.
            Defaults to reading the real file. Only consulted when ``markers`` is
            ``None``.
        read_trajectory: Overridable seam returning the trajectory JSON text.
            Defaults to reading the newest trajectory file.
        merge_commits: Overridable seam — a list of :class:`MergeCommit`. When
            ``None`` (the default), the commits are parsed from the text returned
            by ``read_git_log``.
        read_git_log: Overridable seam returning the git log text. Defaults to
            reading the real reflog. Only consulted when ``merge_commits`` is
            ``None``.

    Returns:
        A :class:`FinalReport`.

    READ-ONLY: the only I/O is through the seams; no process launch, no kill, no
    write. Pure, deterministic, stdlib-only.
    """
    cycles = _expected_cycles(diagnosis)

    obs = observe(cycles, markers=markers, read_cycles_out=read_cycles_out)
    recurrence = report(
        diagnosis,
        markers=markers,
        read_cycles_out=read_cycles_out,
        read_trajectory=read_trajectory,
    )
    git = observe_git(cycles, merge_commits=merge_commits, read_git_log=read_git_log)

    return FinalReport(
        failure_mode=diagnosis.failure_mode,
        recurred=recurrence.recurred,
        observation=obs,
        outcomes=recurrence.outcomes,
        git=git,
        note=_build_final_note(
            diagnosis.failure_mode,
            recurrence.recurred,
            obs,
            git,
        ),
    )


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render(report: FinalReport) -> str:
    """Render a :class:`FinalReport` as deterministic, human-readable text.

    The report answers "did the diagnosed failure mode recur in the observed
    run?" with the following sections, in order:

    * the pipeline failure mode;
    * the marker observation (done / in-flight / gaps);
    * the trajectory outcomes (one line per outcome, file order);
    * the merge-commit status (merged / missing);
    * the RECURRED / clean verdict.

    Pure, deterministic, stdlib-only; READ-ONLY. Stable across a
    :meth:`FinalReport.to_dict` / :meth:`FinalReport.from_dict` round-trip.
    """
    lines: list[str] = []
    lines.append("=== revolver final report ===")
    lines.append(f"failure_mode: {report.failure_mode}")
    lines.append("")
    lines.append("marker observation:")
    lines.append(f"  done: {report.observation.cycles_done}")
    lines.append(f"  in_flight: {report.observation.cycles_in_flight}")
    lines.append(f"  gaps: {report.observation.gaps}")
    lines.append("")
    lines.append("trajectory outcomes:")
    if report.outcomes:
        for o in report.outcomes:
            lines.append(f"  cycle {o.cycle}: {o.outcome}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("merge commits:")
    lines.append(f"  merged: {report.git.cycles_merged}")
    lines.append(f"  missing: {report.git.cycles_missing}")
    lines.append("")
    lines.append(f"verdict: {'RECURRED' if report.recurred else 'clean'}")
    return "\n".join(lines)
