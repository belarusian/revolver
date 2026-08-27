"""Tests for revolver.observe — parse_cycle_markers and observe.

All I/O goes through injectable seams (explicit seam args / patch.object); no
real filesystem is touched and no process is launched or killed. The two
properties the §7 scar and §1 "position is the only order" rule demand are
verified directly: (a) markers are returned in FILE ORDER (never reordered,
never deduped) and (b) gaps are reported honestly (a cycle with no marker is a
gap, never assumed done).
"""

from __future__ import annotations

import json
import re
from unittest.mock import patch

import revolver.observe as observe_module
from revolver.diagnosis import Diagnosis
from revolver.observe import (
    CycleMarker,
    FinalReport,
    GitObservation,
    MergeCommit,
    Observation,
    RecurrenceReport,
    TrajectoryOutcome,
    _is_complete_outcome,
    observe,
    observe_git,
    parse_cycle_markers,
    parse_merge_commits,
    parse_trajectory_outcomes,
    render,
    render_final_report,
    report,
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


# ---------------------------------------------------------------------------
# parse_trajectory_outcomes
# ---------------------------------------------------------------------------


class TestParseTrajectoryOutcomes:
    def test_single_object_complete(self):
        text = json.dumps({"outcome": "exit:task_complete", "messages": []})
        outcomes = parse_trajectory_outcomes(text)
        assert outcomes == [
            TrajectoryOutcome(
                cycle=1,
                outcome="exit:task_complete",
                raw=text,
            )
        ]

    def test_single_object_non_complete(self):
        text = json.dumps({"outcome": "max_steps_reached", "messages": []})
        outcomes = parse_trajectory_outcomes(text)
        assert len(outcomes) == 1
        assert outcomes[0].outcome == "max_steps_reached"
        assert _is_complete_outcome(outcomes[0].outcome) is False

    def test_array_preserves_file_order(self):
        text = json.dumps(
            [
                {"outcome": "max_steps_reached"},
                {"outcome": "error"},
                {"outcome": "exit:task_complete"},
            ]
        )
        outcomes = parse_trajectory_outcomes(text)
        assert [o.outcome for o in outcomes] == [
            "max_steps_reached",
            "error",
            "exit:task_complete",
        ]
        assert [_is_complete_outcome(o.outcome) for o in outcomes] == [
            False,
            False,
            True,
        ]
        # cycle is the 1-based position in file order
        assert [o.cycle for o in outcomes] == [1, 2, 3]

    def test_array_not_reordered_or_deduped(self):
        # position is the only order: duplicates and out-of-order values preserved
        text = json.dumps(
            [
                {"outcome": "error"},
                {"outcome": "error"},
                {"outcome": "exit:task_complete"},
            ]
        )
        outcomes = parse_trajectory_outcomes(text)
        assert [o.outcome for o in outcomes] == ["error", "error", "exit:task_complete"]
        assert len(outcomes) == 3

    def test_malformed_json_returns_empty(self):
        assert parse_trajectory_outcomes("not json at all") == []
        assert parse_trajectory_outcomes("{outcome: broken") == []

    def test_empty_string_returns_empty(self):
        assert parse_trajectory_outcomes("") == []

    def test_non_object_non_array_returns_empty(self):
        assert parse_trajectory_outcomes("42") == []
        assert parse_trajectory_outcomes('"a string"') == []
        assert parse_trajectory_outcomes("null") == []

    def test_object_without_outcome_key(self):
        text = json.dumps({"messages": []})
        outcomes = parse_trajectory_outcomes(text)
        assert len(outcomes) == 1
        assert outcomes[0].outcome == ""
        assert _is_complete_outcome(outcomes[0].outcome) is False

    def test_read_trajectory_seam_injects_fake(self):
        # empty text + seam -> the seam's text is parsed
        fake = json.dumps({"outcome": "error", "messages": []})
        outcomes = parse_trajectory_outcomes("", read_trajectory=lambda: fake)
        assert len(outcomes) == 1
        assert outcomes[0].outcome == "error"

    def test_read_trajectory_seam_not_called_when_text_present(self):
        called = []

        def seam():
            called.append(1)
            return json.dumps({"outcome": "error"})

        text = json.dumps({"outcome": "exit:task_complete"})
        outcomes = parse_trajectory_outcomes(text, read_trajectory=seam)
        assert called == []  # seam not consulted when text is non-empty
        assert _is_complete_outcome(outcomes[0].outcome) is True

    def test_read_trajectory_seam_empty_returns_empty(self):
        assert parse_trajectory_outcomes("", read_trajectory=lambda: "") == []


# ---------------------------------------------------------------------------
# report (recurrence verdict)
# ---------------------------------------------------------------------------


class TestReport:
    def _diag(self, failure_mode, cycles_started, cycles_done=None, cycles_in_flight=None):
        return Diagnosis(
            failure_mode=failure_mode,
            cycles_started=list(cycles_started),
            cycles_done=list(cycles_done or []),
            cycles_in_flight=list(cycles_in_flight or []),
        )

    def test_clean_run_no_recurrence(self):
        d = self._diag("wall-kill", [1, 2], cycles_done=[1, 2])
        markers = [CycleMarker(1, "done", "x"), CycleMarker(2, "done", "y")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert rep.recurred is False
        assert rep.cycles_done == [1, 2]
        assert rep.gaps == []
        assert rep.cycles_in_flight == []
        assert rep.failure_mode == "wall-kill"

    def test_recurred_on_gap(self):
        d = self._diag("driver-death", [1, 2, 3], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert rep.recurred is True
        assert rep.gaps == [2, 3]

    def test_recurred_on_in_flight(self):
        d = self._diag("stall-kill", [1, 2])
        markers = [CycleMarker(1, "done", "x"), CycleMarker(2, "started", "y")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert rep.recurred is True
        assert rep.cycles_in_flight == [2]

    def test_recurred_on_non_complete_outcome(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "max_steps_reached"}),
        )
        assert rep.recurred is True
        assert _is_complete_outcome(rep.outcomes[0].outcome) is False

    def test_recurred_on_error_outcome(self):
        d = self._diag("driver-death", [1], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "error"}),
        )
        assert rep.recurred is True

    def test_no_trajectory_is_clean_when_all_done(self):
        # no trajectory file -> empty outcomes -> clean if all cycles done
        d = self._diag("wall-kill", [1], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(d, markers=markers, read_trajectory=lambda: "")
        assert rep.recurred is False
        assert rep.outcomes == []

    def test_cycles_from_done_plus_in_flight_when_started_empty(self):
        # cycles_started empty -> falls back to cycles_done + cycles_in_flight
        d = Diagnosis(
            failure_mode="wall-kill",
            cycles_started=[],
            cycles_done=[1],
            cycles_in_flight=[2],
        )
        markers = [CycleMarker(1, "done", "x"), CycleMarker(2, "started", "y")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert rep.recurred is True
        assert rep.cycles_in_flight == [2]

    def test_failure_mode_reported_verbatim(self):
        d = self._diag("some-odd-mode", [1], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert rep.failure_mode == "some-odd-mode"

    def test_read_cycles_out_seam_used_when_markers_none(self):
        d = self._diag("driver-death", [1, 2], cycles_done=[1])
        cycles_out = "========== CYCLE 1 done ==========\n"
        rep = report(
            d,
            read_cycles_out=lambda: cycles_out,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert rep.recurred is True  # cycle 2 is a gap
        assert rep.gaps == [2]

    def test_round_trip(self):
        d = self._diag("driver-death", [1, 2, 3], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "error"}),
        )
        assert RecurrenceReport.from_dict(rep.to_dict()) == rep

    def test_to_dict_keys(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        rep = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        assert set(rep.to_dict()) == {
            "failure_mode",
            "recurred",
            "cycles_done",
            "cycles_in_flight",
            "gaps",
            "outcomes",
            "note",
        }


# ---------------------------------------------------------------------------
# parse_merge_commits
# ---------------------------------------------------------------------------


class TestParseMergeCommits:
    def test_single_commit(self):
        text = "d38efa5 Merge pull request #65 from belarusian/build11/trajectory-recurrence\n"
        commits = parse_merge_commits(text)
        assert len(commits) == 1
        assert commits[0].cycle == 11
        assert commits[0].sha == "d38efa5"
        assert commits[0].raw == text.strip()

    def test_multiple_commits(self):
        text = (
            "d38efa5 Merge pull request #65 from belarusian/build11/trajectory-recurrence\n"
            "4b93508 feat: not a merge\n"
            "6fd64f8 Merge pull request #59 from belarusian/build10/observe-report\n"
        )
        commits = parse_merge_commits(text)
        assert [c.cycle for c in commits] == [11, 10]
        assert [c.sha for c in commits] == ["d38efa5", "6fd64f8"]

    def test_file_order_preserved(self):
        # the file order (newest first) is preserved, never sorted
        text = (
            "aaa Merge pull request #1 from o/build3/x\n"
            "bbb Merge pull request #2 from o/build1/x\n"
            "ccc Merge pull request #3 from o/build2/x\n"
        )
        commits = parse_merge_commits(text)
        assert [c.cycle for c in commits] == [3, 1, 2]

    def test_no_reorder_no_dedupe(self):
        # a cycle may have more than one merge across restarts; never deduped
        text = (
            "aaa Merge pull request #1 from o/build5/x\n"
            "bbb Merge pull request #2 from o/build5/y\n"
            "ccc Merge pull request #3 from o/build5/z\n"
        )
        commits = parse_merge_commits(text)
        assert [c.cycle for c in commits] == [5, 5, 5]
        assert len(commits) == 3

    def test_empty_text(self):
        assert parse_merge_commits("") == []

    def test_no_match_returns_empty(self):
        text = "4b93508 feat: revolver.observe — no merge here\n"
        assert parse_merge_commits(text) == []

    def test_custom_merge_pattern_seam(self):
        # inject a custom dialect: capture the cycle from a different convention
        import re

        pattern = re.compile(r"cycle-(\d+) merged")
        text = "aaa1111 cycle-7 merged\nbbb2222 cycle-8 merged\n"
        commits = parse_merge_commits(text, merge_pattern=pattern)
        assert [c.cycle for c in commits] == [7, 8]
        assert [c.sha for c in commits] == ["aaa1111", "bbb2222"]

    def test_line_without_leading_sha(self):
        # a merge line with no leading sha token -> sha is the empty string
        text = "Merge pull request #1 from o/build4/x\n"
        commits = parse_merge_commits(text)
        assert commits[0].cycle == 4
        assert commits[0].sha == ""


# ---------------------------------------------------------------------------
# observe_git
# ---------------------------------------------------------------------------


class TestObserveGit:
    def test_all_merged(self):
        commits = [MergeCommit(1, "a", "x"), MergeCommit(2, "b", "y")]
        obs = observe_git([1, 2], merge_commits=commits)
        assert obs.cycles_merged == [1, 2]
        assert obs.cycles_missing == []

    def test_some_missing(self):
        commits = [MergeCommit(1, "a", "x")]
        obs = observe_git([1, 2, 3], merge_commits=commits)
        assert obs.cycles_merged == [1]
        assert obs.cycles_missing == [2, 3]

    def test_empty_cycles(self):
        obs = observe_git([], merge_commits=[MergeCommit(1, "a", "x")])
        assert obs.cycles_merged == []
        assert obs.cycles_missing == []

    def test_output_preserves_input_order(self):
        commits = [MergeCommit(3, "a", "x"), MergeCommit(1, "b", "y")]
        obs = observe_git([3, 1, 2], merge_commits=commits)
        assert obs.cycles_merged == [3, 1]
        assert obs.cycles_missing == [2]

    def test_duplicate_merge_commits_not_deduped_in_observation(self):
        # a cycle with two merges is still reported merged once (set membership)
        commits = [MergeCommit(1, "a", "x"), MergeCommit(1, "b", "y")]
        obs = observe_git([1, 2], merge_commits=commits)
        assert obs.cycles_merged == [1]
        assert obs.cycles_missing == [2]

    def test_read_git_log_seam(self):
        # when merge_commits is None, read_git_log is consulted and parsed
        text = "aaa Merge pull request #1 from o/build1/x\n"
        obs = observe_git([1, 2], read_git_log=lambda: text)
        assert obs.cycles_merged == [1]
        assert obs.cycles_missing == [2]

    def test_injected_merge_commits_default_never_called(self):
        # when merge_commits is injected, the default git-log read is never resolved
        with patch.object(
            observe_module,
            "_default_read_git_log",
            side_effect=AssertionError("default read must not be called"),
        ):
            obs = observe_git([1], merge_commits=[MergeCommit(1, "a", "x")])
        assert obs.cycles_merged == [1]

    def test_default_read_used_when_no_seams(self):
        # with both seams None, the default seam is consulted (patched so the
        # real filesystem is never touched)
        text = "aaa Merge pull request #1 from o/build1/x\n"
        with patch.object(observe_module, "_default_read_git_log", return_value=text):
            obs = observe_git([1, 2])
        assert obs.cycles_merged == [1]
        assert obs.cycles_missing == [2]

    def test_round_trip(self):
        obs = observe_git([1, 2], merge_commits=[MergeCommit(1, "a", "x")])
        assert GitObservation.from_dict(obs.to_dict()) == obs

    def test_to_dict_keys(self):
        obs = observe_git([1], merge_commits=[MergeCommit(1, "a", "x")])
        assert set(obs.to_dict()) == {"cycles_merged", "cycles_missing", "note"}


# ---------------------------------------------------------------------------
# render_final_report + render
# ---------------------------------------------------------------------------


class TestRenderFinalReport:
    def _diag(self, failure_mode, cycles_started, cycles_done=None, cycles_in_flight=None):
        return Diagnosis(
            failure_mode=failure_mode,
            cycles_started=list(cycles_started),
            cycles_done=list(cycles_done or []),
            cycles_in_flight=list(cycles_in_flight or []),
        )

    def test_clean_run_recurred_false(self):
        d = self._diag("wall-kill", [1, 2], cycles_done=[1, 2])
        markers = [CycleMarker(1, "done", "x"), CycleMarker(2, "done", "y")]
        commits = [MergeCommit(1, "a", "x"), MergeCommit(2, "b", "y")]
        rep = render_final_report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=commits,
        )
        assert rep.recurred is False
        assert rep.failure_mode == "wall-kill"
        assert rep.observation.cycles_done == [1, 2]
        assert rep.git.cycles_merged == [1, 2]
        assert rep.git.cycles_missing == []

    def test_recurrence_recurred_true(self):
        # a gap (cycle 2 has no marker) -> recurred True
        d = self._diag("driver-death", [1, 2], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        commits = [MergeCommit(1, "a", "x")]
        rep = render_final_report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=commits,
        )
        assert rep.recurred is True
        assert rep.observation.gaps == [2]

    def test_git_missing_feeds_the_report(self):
        # a missing merge commit is reported in the git observation (honest)
        d = self._diag("wall-kill", [1, 2], cycles_done=[1, 2])
        markers = [CycleMarker(1, "done", "x"), CycleMarker(2, "done", "y")]
        commits = [MergeCommit(1, "a", "x")]  # cycle 2 has no merge commit
        rep = render_final_report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=commits,
        )
        assert rep.git.cycles_merged == [1]
        assert rep.git.cycles_missing == [2]

    def test_empty_inputs(self):
        d = self._diag("none", [])
        rep = render_final_report(
            d,
            markers=[],
            read_trajectory=lambda: "",
            merge_commits=[],
        )
        assert rep.recurred is False
        assert rep.observation.cycles_done == []
        assert rep.git.cycles_merged == []
        assert rep.git.cycles_missing == []

    def test_custom_markers_seam(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        rep = render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x")],
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=[MergeCommit(1, "a", "x")],
        )
        assert rep.observation.cycles_done == [1]

    def test_custom_read_cycles_out_seam(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        text = "========== CYCLE 1 done ==========\n"
        rep = render_final_report(
            d,
            read_cycles_out=lambda: text,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=[MergeCommit(1, "a", "x")],
        )
        assert rep.observation.cycles_done == [1]

    def test_custom_read_trajectory_seam(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        rep = render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x")],
            read_trajectory=lambda: json.dumps({"outcome": "error"}),
            merge_commits=[MergeCommit(1, "a", "x")],
        )
        assert rep.recurred is True  # non-complete outcome
        assert rep.outcomes[0].outcome == "error"

    def test_custom_read_git_log_seam(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        text = "aaa Merge pull request #1 from o/build1/x\n"
        rep = render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x")],
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            read_git_log=lambda: text,
        )
        assert rep.git.cycles_merged == [1]

    def test_recurred_is_reused_not_rederived(self):
        # the verdict matches the Cycle 11 report() output exactly
        d = self._diag("driver-death", [1, 2], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        commits = [MergeCommit(1, "a", "x")]
        rec = report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
        )
        rep = render_final_report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=commits,
        )
        assert rep.recurred == rec.recurred
        assert rep.outcomes == rec.outcomes

    def test_round_trip(self):
        d = self._diag("driver-death", [1, 2], cycles_done=[1])
        markers = [CycleMarker(1, "done", "x")]
        commits = [MergeCommit(1, "a", "x")]
        rep = render_final_report(
            d,
            markers=markers,
            read_trajectory=lambda: json.dumps({"outcome": "error"}),
            merge_commits=commits,
        )
        assert FinalReport.from_dict(rep.to_dict()) == rep

    def test_to_dict_keys(self):
        d = self._diag("wall-kill", [1], cycles_done=[1])
        rep = render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x")],
            read_trajectory=lambda: json.dumps({"outcome": "exit:task_complete"}),
            merge_commits=[MergeCommit(1, "a", "x")],
        )
        assert set(rep.to_dict()) == {
            "failure_mode",
            "recurred",
            "observation",
            "outcomes",
            "git",
            "note",
        }


class TestRender:
    def _clean_report(self):
        d = Diagnosis(
            failure_mode="wall-kill",
            cycles_started=[1, 2],
            cycles_done=[1, 2],
        )
        return render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x"), CycleMarker(2, "done", "y")],
            read_trajectory=lambda: json.dumps(
                [{"outcome": "exit:task_complete"}, {"outcome": "exit:task_complete"}]
            ),
            merge_commits=[MergeCommit(1, "a", "x"), MergeCommit(2, "b", "y")],
        )

    def test_render_clean_verdict(self):
        text = render(self._clean_report())
        assert "verdict: clean" in text
        assert "failure_mode: wall-kill" in text

    def test_render_recurred_verdict(self):
        d = Diagnosis(failure_mode="driver-death", cycles_started=[1, 2], cycles_done=[1])
        rep = render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x")],
            read_trajectory=lambda: json.dumps({"outcome": "error"}),
            merge_commits=[MergeCommit(1, "a", "x")],
        )
        text = render(rep)
        assert "verdict: RECURRED" in text

    def test_render_embeds_each_section(self):
        text = render(self._clean_report())
        assert "marker observation:" in text
        assert "trajectory outcomes:" in text
        assert "merge commits:" in text
        assert "done: [1, 2]" in text
        assert "merged: [1, 2]" in text
        assert "missing: []" in text
        assert "cycle 1: exit:task_complete" in text
        assert "cycle 2: exit:task_complete" in text

    def test_render_deterministic(self):
        a = render(self._clean_report())
        b = render(self._clean_report())
        assert a == b

    def test_render_stable_across_round_trip(self):
        rep = self._clean_report()
        restored = FinalReport.from_dict(rep.to_dict())
        assert render(rep) == render(restored)

    def test_render_empty_outcomes(self):
        d = Diagnosis(failure_mode="none", cycles_started=[1], cycles_done=[1])
        rep = render_final_report(
            d,
            markers=[CycleMarker(1, "done", "x")],
            read_trajectory=lambda: "",
            merge_commits=[MergeCommit(1, "a", "x")],
        )
        text = render(rep)
        assert "(none)" in text
