"""Tests for revolver.observe — parse_cycle_markers and observe.

All I/O goes through injectable seams (explicit seam args / patch.object); no
real filesystem is touched and no process is launched or killed. The two
properties the §7 scar and §1 "position is the only order" rule demand are
verified directly: (a) markers are returned in FILE ORDER (never reordered,
never deduped) and (b) gaps are reported honestly (a cycle with no marker is a
gap, never assumed done).
"""

from __future__ import annotations

import re
from unittest.mock import patch

import revolver.observe as observe_module
from revolver.observe import (
    CycleMarker,
    Observation,
    observe,
    parse_cycle_markers,
)

# ---------------------------------------------------------------------------
# parse_cycle_markers
# ---------------------------------------------------------------------------


class TestParseCycleMarkers:
    def test_done_marker(self):
        text = "========== CYCLE 1 done ==========\n"
        markers = parse_cycle_markers(text)
        assert markers == [CycleMarker(cycle=1, status="done", raw=text.rstrip("\n"))]
        assert markers[0].status == "done"
        assert markers[0].cycle == 1

    def test_started_marker(self):
        text = "========== CYCLE 1 ==========\n"
        markers = parse_cycle_markers(text)
        assert markers == [CycleMarker(cycle=1, status="started", raw=text.rstrip("\n"))]
        assert markers[0].status == "started"

    def test_mixed_text(self):
        text = (
            "========== CYCLE 1  2025-01-01 10:00:00Z ==========\n"
            "some output\n"
            "========== CYCLE 1 done ==========\n"
            "========== CYCLE 2  2025-01-01 11:00:00Z ==========\n"
            "more output\n"
        )
        markers = parse_cycle_markers(text)
        assert [m.cycle for m in markers] == [1, 1, 2]
        assert [m.status for m in markers] == ["started", "done", "started"]
        # non-marker lines are skipped
        assert len(markers) == 3

    def test_out_of_order_preserved_in_file_order(self):
        # position is the only order: NOT sorted by cycle number
        text = (
            "========== CYCLE 3 ==========\n"
            "========== CYCLE 1 done ==========\n"
            "========== CYCLE 2 ==========\n"
        )
        markers = parse_cycle_markers(text)
        assert [m.cycle for m in markers] == [3, 1, 2]
        assert [m.status for m in markers] == ["started", "done", "started"]

    def test_no_dedupe_across_restarts(self):
        # a cycle may appear more than once; never deduped by cycle number
        text = (
            "========== CYCLE 1 ==========\n"
            "========== CYCLE 1 done ==========\n"
            "========== CYCLE 1 ==========\n"
        )
        markers = parse_cycle_markers(text)
        assert len(markers) == 3
        assert [m.status for m in markers] == ["started", "done", "started"]

    def test_custom_done_pattern_seam(self):
        # inject a different dialect: "COMPLETE" instead of "done"
        text = (
            "========== CYCLE 1 COMPLETE ==========\n"
            "========== CYCLE 2 ==========\n"
        )
        # with the DEFAULT pattern, "COMPLETE" is not "done" -> both started
        default_markers = parse_cycle_markers(text)
        assert [m.status for m in default_markers] == ["started", "started"]

        # with the custom seam, "COMPLETE" counts as done
        custom = re.compile(r"^=+\s*CYCLE\s+(\d+)\s+COMPLETE\b")
        markers = parse_cycle_markers(text, done_pattern=custom)
        assert [m.status for m in markers] == ["done", "started"]

    def test_empty_text(self):
        assert parse_cycle_markers("") == []

    def test_no_markers_in_text(self):
        assert parse_cycle_markers("just some log output\nno cycle lines\n") == []

    def test_raw_preserves_original_line(self):
        line = "========== CYCLE 7  2025-01-01 =========="
        markers = parse_cycle_markers(line + "\n")
        assert markers[0].raw == line


# ---------------------------------------------------------------------------
# observe
# ---------------------------------------------------------------------------


class TestObserve:
    def test_all_done(self):
        markers = [
            CycleMarker(1, "done", "x"),
            CycleMarker(2, "done", "y"),
            CycleMarker(3, "done", "z"),
        ]
        obs = observe([1, 2, 3], markers=markers)
        assert isinstance(obs, Observation)
        assert obs.cycles_done == [1, 2, 3]
        assert obs.cycles_in_flight == []
        assert obs.cycles_seen == [1, 2, 3]
        assert obs.gaps == []

    def test_some_in_flight(self):
        markers = [
            CycleMarker(1, "done", "x"),
            CycleMarker(2, "started", "y"),
            CycleMarker(3, "done", "z"),
        ]
        obs = observe([1, 2, 3], markers=markers)
        assert obs.cycles_done == [1, 3]
        assert obs.cycles_in_flight == [2]
        assert obs.cycles_seen == [1, 2, 3]
        assert obs.gaps == []

    def test_gaps_reported_honestly(self):
        # a cycle with no marker is a gap, NOT assumed done
        markers = [CycleMarker(1, "done", "x")]
        obs = observe([1, 2, 3], markers=markers)
        assert obs.cycles_done == [1]
        assert obs.cycles_in_flight == []
        assert obs.cycles_seen == [1]
        assert obs.gaps == [2, 3]
        assert "gaps" in obs.note

    def test_empty_cycles(self):
        obs = observe([], markers=[])
        assert obs.cycles_seen == []
        assert obs.cycles_done == []
        assert obs.cycles_in_flight == []
        assert obs.gaps == []
        assert obs.note == "no cycles to observe"

    def test_custom_markers_seam(self):
        # inject a list[CycleMarker] directly; read_cycles_out never consulted
        markers = [CycleMarker(5, "started", "raw")]
        obs = observe([5, 6], markers=markers)
        assert obs.cycles_in_flight == [5]
        assert obs.gaps == [6]
        assert obs.cycles_seen == [5]

    def test_read_cycles_out_seam(self):
        # inject a fake reader; markers=None so the reader is consulted
        text = "========== CYCLE 1 ==========\n========== CYCLE 1 done ==========\n"
        calls: list[int] = []

        def fake_read() -> str:
            calls.append(1)
            return text

        obs = observe([1, 2], read_cycles_out=fake_read)
        assert calls == [1]
        assert obs.cycles_done == [1]
        assert obs.cycles_in_flight == []
        assert obs.gaps == [2]

    def test_injected_read_cycles_out_default_never_called(self):
        # when read_cycles_out is injected, the default (real file read) is never
        # resolved or called
        text = "========== CYCLE 1 ==========\n"
        with patch.object(
            observe_module,
            "_default_read_cycles_out",
            side_effect=AssertionError("default read must not be called"),
        ):
            obs = observe([1], read_cycles_out=lambda: text)
        assert obs.cycles_in_flight == [1]

    def test_default_read_used_when_no_seams(self):
        # with both seams None, the default seam is the one consulted (patched so
        # the real filesystem is never touched)
        text = "========== CYCLE 1 done ==========\n"
        with patch.object(
            observe_module, "_default_read_cycles_out", return_value=text
        ):
            obs = observe([1, 2])
        assert obs.cycles_done == [1]
        assert obs.gaps == [2]

    def test_done_wins_over_started(self):
        # a cycle with both a started and a done marker is done
        markers = [
            CycleMarker(1, "started", "x"),
            CycleMarker(1, "done", "y"),
        ]
        obs = observe([1], markers=markers)
        assert obs.cycles_done == [1]
        assert obs.cycles_in_flight == []

    def test_output_preserves_input_order(self):
        # output lists follow the input `cycles` order, not sorted
        markers = [
            CycleMarker(3, "done", "x"),
            CycleMarker(1, "done", "y"),
        ]
        obs = observe([3, 1, 2], markers=markers)
        assert obs.cycles_done == [3, 1]
        assert obs.gaps == [2]

    def test_markers_outside_cycles_ignored(self):
        # markers for cycles not in the input are not reported anywhere
        markers = [
            CycleMarker(99, "done", "x"),
            CycleMarker(1, "done", "y"),
        ]
        obs = observe([1, 2], markers=markers)
        assert obs.cycles_done == [1]
        assert obs.gaps == [2]
        assert 99 not in obs.cycles_seen
        assert 99 not in obs.cycles_done

    def test_round_trip(self):
        obs = observe([1, 2, 3], markers=[CycleMarker(1, "done", "x")])
        assert Observation.from_dict(obs.to_dict()) == obs

    def test_to_dict_keys(self):
        obs = observe([1], markers=[CycleMarker(1, "done", "x")])
        assert set(obs.to_dict()) == {
            "cycles_seen",
            "cycles_done",
            "cycles_in_flight",
            "gaps",
            "note",
        }
