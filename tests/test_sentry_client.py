"""Tests for revolver.sentry_client — runner-seam tests.

Covers: check stdout -> Diagnosis round-trip; exit-code passthrough (0/1/2);
not-importable -> raw-artifacts fallback. Uses ``patch.object(instance, "run_check")``
(Rule 4) so nothing ever shells out.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from revolver.diagnosis import diagnose
from revolver.sentry_client import SentryClient, diagnose_via_sentry

# A canned 8-line sentry check report (the stable dialect).
REPORT_ACTION = (
    "driver: dead\n"
    "driver-death: DETECTED cycle 8\n"
    "wall-kill-no-merge: none\n"
    "stall: none (no stall detected)\n"
    "live work: no\n"
    "cycles: started=[1, 2, 3, 8] done=[1, 2, 3] in_flight=[8] wall_kill=[]\n"
    "gate-blocks: []\n"
    "verdict: ACTION NEEDED\n"
)

REPORT_HEALTHY = (
    "driver: alive\n"
    "driver-death: none\n"
    "wall-kill-no-merge: none\n"
    "stall: none (no stall detected)\n"
    "live work: no\n"
    "cycles: started=[1, 2, 3] done=[1, 2, 3] in_flight=[] wall_kill=[]\n"
    "gate-blocks: []\n"
    "verdict: HEALTHY\n"
)


class TestDiagnoseViaSentry:
    def test_exit_1_action_needed(self):
        client = SentryClient()
        with patch.object(client, "run_check", return_value=(REPORT_ACTION, 1)):
            d = diagnose_via_sentry("/tmp/proj", client=client)
        assert d.source == "sentry-report"
        assert d.action_needed is True
        assert d.exit_code == 1
        assert d.sentry_exit_code == 1
        assert d.driver_death_cycle == 8
        assert d.verdict == "ACTION NEEDED"

    def test_exit_0_healthy(self):
        client = SentryClient()
        with patch.object(client, "run_check", return_value=(REPORT_HEALTHY, 0)):
            d = diagnose_via_sentry("/tmp/proj", client=client)
        assert d.source == "sentry-report"
        assert d.action_needed is False
        assert d.exit_code == 0
        assert d.sentry_exit_code == 0
        assert d.verdict == "HEALTHY"

    def test_exit_2_usage_error(self):
        client = SentryClient()
        with patch.object(client, "run_check", return_value=(REPORT_HEALTHY, 2)):
            d = diagnose_via_sentry("/tmp/proj", client=client)
        assert d.source == "sentry-report"
        assert d.exit_code == 2
        assert d.sentry_exit_code == 2
        assert "usage error" in d.evidence
        assert "2" in d.evidence

    def test_default_client_used_when_none(self):
        # No client passed; patch the class-level seam so the default instance hits it.
        with patch.object(SentryClient, "run_check", return_value=(REPORT_HEALTHY, 0)):
            d = diagnose_via_sentry("/tmp/proj")
        assert d.source == "sentry-report"
        assert d.exit_code == 0


class TestDiagnoseFallback:
    def test_sentry_not_importable_falls_back(self, tmp_path: Path):
        (tmp_path / "cycles.out").write_text(
            "========== CYCLE 1  2025-01-01 ==========\n"
            "========== CYCLE 1 done ==========\n"
        )
        client = SentryClient()
        with patch.object(client, "run_check", side_effect=ImportError("no sentry")):
            d = diagnose(tmp_path, sentry_available=True, client=client)
        assert d.source == "raw-artifacts"
        assert "sentry unavailable" in d.evidence
        assert d.cycles_done == [1]

    def test_sentry_runner_failure_falls_back(self, tmp_path: Path):
        (tmp_path / "cycles.out").write_text(
            "========== CYCLE 2  2025-01-01 ==========\n"
        )
        client = SentryClient()
        with patch.object(client, "run_check", side_effect=RuntimeError("boom")):
            d = diagnose(tmp_path, sentry_available=True, client=client)
        assert d.source == "raw-artifacts"
        assert "sentry runner failed" in d.evidence
        assert d.cycles_started == [2]

    def test_sentry_available_returns_sentry_report(self, tmp_path: Path):
        client = SentryClient()
        with patch.object(client, "run_check", return_value=(REPORT_ACTION, 1)):
            d = diagnose(tmp_path, sentry_available=True, client=client)
        assert d.source == "sentry-report"
        assert d.exit_code == 1
        assert d.action_needed is True
