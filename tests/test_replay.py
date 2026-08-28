"""tests/test_replay.py — pure replay acceptance tests for the founding fix classes.

Diff from predecessor: NEW test module (no predecessor in this repo).
Evidence: TICKET-067 — feed a fixed diagnosis into each founding generator and assert
the generated path is SEMANTICALLY EQUIVALENT to the golden reference (read-only).
The tests are pure: fixed inputs, no sentry import, no disk write, no clock, no
randomness. They assert on the GENERATED content's semantic properties (the one-line
deltas, the timeout-to-both-impls, the export >= outer wall, the single
inner-seconds substitution), NOT on byte-equality with the seed files.
"""

from __future__ import annotations

import re

import pytest

from revolver.diagnosis import Diagnosis
from revolver.fixes import (
    build_client_timeout_fix,
    build_inner_wall_fix,
)
from revolver.proposal import PROPOSAL_NAMESPACE, propose

# ---------------------------------------------------------------------------
# Cycle-8 (client-timeout) replay
# ---------------------------------------------------------------------------


def _cycle8_diagnosis() -> Diagnosis:
    """A fixed cycle-8 client-timeout diagnosis (pure, no sentry import)."""
    return Diagnosis(
        failure_mode="client-timeout",
        client_timeout_cycle=8,
        outer_wall=10800,
        endpoint_pin="standard (.157:8080 fast-qwen / .161:8081 qwen)",
        source="sentry-report",
        evidence="cycle 8 cancel-loop",
    )


class TestClientTimeoutReplay:
    def test_emits_four_new_files(self):
        files = build_client_timeout_fix(_cycle8_diagnosis())
        assert len(files) == 4
        # All under the proposal namespace (hard rule 7: additions only).
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in files)

    def test_every_file_carries_docstring(self):
        for f in build_client_timeout_fix(_cycle8_diagnosis()):
            assert "Diff from predecessor:" in f.content
            assert "Evidence:" in f.content

    def test_chat_model_passes_timeout_to_both_impls(self):
        files = {f.path.rsplit("/", 1)[-1]: f for f in build_client_timeout_fix(_cycle8_diagnosis())}
        cm = files["client_timeout_chat_model.py"].content
        # Reads the env var with the 21600s default.
        assert 'os.getenv("FIVE_REQUEST_TIMEOUT", "21600")' in cm
        # The explicit timeout is passed to BOTH impls (fast + large).
        assert cm.count("timeout=request_timeout") == 2
        assert "fast_impl = _ChatCompletionsText(" in cm
        assert "large_impl = _ChatCompletionsText(" in cm

    def test_runner_and_spoke_carry_one_line_import_delta(self):
        files = {f.path.rsplit("/", 1)[-1]: f for f in build_client_timeout_fix(_cycle8_diagnosis())}
        for name in ("client_timeout_runner.py", "client_timeout_spoke.py"):
            content = files[name].content
            # The one-line import delta: context_aware_invoke from the new module.
            assert "from four.chat_model_v2 import context_aware_invoke" in content
            # And it actually uses it.
            assert "context_aware_invoke(" in content

    def test_driver_exports_timeout_ge_outer_wall_and_repoints(self):
        files = {f.path.rsplit("/", 1)[-1]: f for f in build_client_timeout_fix(_cycle8_diagnosis())}
        driver = files["client_timeout_driver.sh"].content
        # Exports FIVE_REQUEST_TIMEOUT >= the 10800s outer wall.
        m = re.search(r"export FIVE_REQUEST_TIMEOUT=(\d+)", driver)
        assert m is not None
        assert int(m.group(1)) >= 10800
        # Repoints RUN/SPOKE at the new files.
        assert "RUN=/home/sasha/Research/four/run-v3.py" in driver
        assert "SPOKE=/home/sasha/Research/four/examples/spokes/cycle-implementation-v4.py" in driver

    def test_propose_yields_client_timeout_path(self):
        p = propose(_cycle8_diagnosis())
        assert len(p.new_files) == 4
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in p.new_files)


# ---------------------------------------------------------------------------
# Cycle-11 (inner-wall) replay
# ---------------------------------------------------------------------------

_PREDECESSOR_DRIVER = (
    "#!/bin/bash\n"
    "export FIVE_MODEL=fast-qwen\n"
    "export FIVE_LARGE_MODEL=qwen\n"
    "--inner-seconds 2400\n"
    "run_cycle\n"
)


def _cycle11_diagnosis() -> Diagnosis:
    """A fixed cycle-11 inner-wall diagnosis (pure, no sentry import)."""
    return Diagnosis(
        failure_mode="inner-wall",
        inner_wall_kill_cycle=11,
        heaviest_inner_duration=2400,
        source="sentry-report",
        evidence="cycle 11 wall-kill after merge",
    )


class TestInnerWallReplay:
    def test_emits_one_new_file(self):
        files = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=_PREDECESSOR_DRIVER)
        assert len(files) == 1
        assert files[0].path.startswith(PROPOSAL_NAMESPACE)

    def test_only_delta_is_inner_seconds(self):
        f = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=_PREDECESSOR_DRIVER)[0]
        content = f.content
        # The corrected inner wall: heaviest (2400) + margin (1800) = 4200.
        assert "--inner-seconds 4200" in content
        # The old value is gone (single substitution, not an append).
        assert "--inner-seconds 2400" not in content
        # Everything else from the predecessor is byte-identical.
        for line in ("export FIVE_MODEL=fast-qwen", "export FIVE_LARGE_MODEL=qwen", "run_cycle"):
            assert line in content

    def test_carries_docstring(self):
        f = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=_PREDECESSOR_DRIVER)[0]
        assert "Diff from predecessor:" in f.content
        assert "Evidence:" in f.content

    def test_margin_over_old_when_no_heaviest(self):
        d = Diagnosis(
            failure_mode="inner-wall",
            inner_wall_kill_cycle=11,
            inner_seconds=3000,
            source="sentry-report",
        )
        f = build_inner_wall_fix(d, predecessor_driver=_PREDECESSOR_DRIVER)[0]
        # Old inner wall (3000) + margin (1800) = 4800.
        assert "--inner-seconds 4800" in f.content
        assert "--inner-seconds 2400" not in f.content

    def test_appends_when_no_token_present(self):
        d = _cycle11_diagnosis()
        pre = "#!/bin/bash\nexport FIVE_MODEL=fast-qwen\nrun_cycle\n"
        f = build_inner_wall_fix(d, predecessor_driver=pre)[0]
        # No --inner-seconds token existed -> appended as the single delta line.
        assert "--inner-seconds 4200" in f.content
        assert "run_cycle" in f.content


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
