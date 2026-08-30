"""tests/test_replay.py — pure replay acceptance tests for the founding fix classes.

Diff from predecessor: NEW test module (no predecessor in this repo).
Evidence: TICKET-067 — feed a fixed diagnosis into each founding generator and assert
the generated path is SEMANTICALLY EQUIVALENT to the golden reference (read-only).
The tests are pure: fixed inputs, no sentry import, no disk write, no clock, no
randomness. They assert on the GENERATED content's semantic properties (the one-line
deltas, the timeout-to-both-impls, the export >= outer wall, the single
inner-seconds substitution), NOT on byte-equality with the seed files.

TICKET-078: Replaced docstring-grep assertions with execution-based tests:
  - py_compile every generated .py file
  - import-resolution (exec runner with staged chat-model)
  - driver parsing (RUN=/SPOKE= point at staged paths)
  - diff isolation (difflib diff vs predecessor == stated lines)
  - recurrence semantics (kept from prior cycle)
  - negative test (broken instruction fails at derive time)
"""

from __future__ import annotations

import difflib
import py_compile
import re
import sys
import tempfile
from pathlib import Path

import pytest

from revolver.diagnosis import Diagnosis
from revolver.fixes import (
    build_client_timeout_fix,
    build_inner_wall_fix,
    build_outer_freshness_fix,
)
from revolver.proposal import PROPOSAL_NAMESPACE, propose

# ---------------------------------------------------------------------------
# Triple-path resolution (execution-plane only; skip in CI)
# ---------------------------------------------------------------------------

_TRIPLE_DIR = Path.home() / "AI" / "revolver" / "triple"


def _triple_available() -> bool:
    """True when the execution-plane triple directory exists (local plane)."""
    return _TRIPLE_DIR.is_dir()


requires_triple = pytest.mark.skipif(
    not _triple_available(),
    reason="triple/ directory not present (CI lens); execution-plane only",
)


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

    def test_all_py_files_compile(self):
        """Every generated .py file is syntactically valid Python (py_compile)."""
        for f in build_client_timeout_fix(_cycle8_diagnosis()):
            if f.path.endswith(".py"):
                with tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w", delete=False, encoding="utf-8"
                ) as tmp:
                    tmp.write(f.content)
                    tmp_path = tmp.name
                try:
                    py_compile.compile(tmp_path, doraise=True)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

    def test_import_resolution(self, tmp_path: Path):
        """Exec the generated runner in a namespace where the staged chat-model
        module satisfies its import — proves the emitted import points at the
        staged file, not a re-typed body."""
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_client_timeout_fix(_cycle8_diagnosis())
        }
        # Stage the chat-model as four/chat_model_v2.py in a temp package.
        # Also stage four/chat_model.py (the base module that chat_model_v2
        # imports _ChatCompletionsText from).
        pkg_dir = tmp_path / "four"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        # Minimal base module providing _ChatCompletionsText.
        (pkg_dir / "chat_model.py").write_text(
            "class _ChatCompletionsText:\n"
            "    def __init__(self, model, base_url, api_key, timeout=None):\n"
            "        self.model = model\n"
            "        self.timeout = timeout\n"
            "    def __call__(self, messages):\n"
            "        return 'ok'\n",
            encoding="utf-8",
        )
        (pkg_dir / "chat_model_v2.py").write_text(
            files["client_timeout_chat_model.py"].content, encoding="utf-8"
        )
        # Add the temp dir to sys.path so `four.chat_model_v2` resolves.
        sys.path.insert(0, str(tmp_path))
        try:
            # Import the staged module — proves it's valid and has the symbol.
            import importlib

            mod = importlib.import_module("four.chat_model_v2")
            assert hasattr(mod, "context_aware_invoke")
            # Now exec the runner's import line in a namespace that can resolve
            # the staged module.
            runner_content = files["client_timeout_runner.py"].content
            import_line = next(
                ln
                for ln in runner_content.splitlines()
                if "from four.chat_model_v2 import" in ln
            )
            ns: dict = {}
            exec(import_line, ns)
            assert "context_aware_invoke" in ns
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up the imported module so it doesn't leak.
            sys.modules.pop("four.chat_model_v2", None)
            sys.modules.pop("four.chat_model", None)
            sys.modules.pop("four", None)

    def test_diff_isolation(self):
        """For the generated chat-model, difflib diff vs its predecessor ==
        exactly the instruction's stated lines (byte-identity of everything else)."""
        files = build_client_timeout_fix(_cycle8_diagnosis())
        # The chat-model predecessor is the pinned triple file.
        pred_cm = _TRIPLE_DIR / "chat_model.py"
        if not pred_cm.exists():
            pytest.skip("triple/chat_model.py not present")
        pred_text = pred_cm.read_text(encoding="utf-8")
        gen_cm = next(
            f
            for f in files
            if f.path.rsplit("/", 1)[-1] == "client_timeout_chat_model.py"
        )
        # Strip the derive header (docstring block) from the generated content
        # to get the pure body for diffing.
        gen_body = _strip_derive_header(gen_cm.content, is_py=True)
        pred_lines = pred_text.splitlines(keepends=True)
        gen_lines = gen_body.splitlines(keepends=True)
        diff = list(difflib.unified_diff(pred_lines, gen_lines, n=0))
        # The diff should be non-empty (there IS a change) and limited to
        # the stated replacement line.
        assert len(diff) > 0, "expected a non-empty diff"
        # Count changed lines (excluding headers): should be exactly 1 deletion
        # and 1 addition (a single-line replacement).
        deletions = [ln for ln in diff if ln.startswith("-") and not ln.startswith("---")]
        additions = [ln for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
        assert len(deletions) == 1, (
            f"expected 1 deletion, got {len(deletions)}: {deletions}"
        )
        assert len(additions) == 1, (
            f"expected 1 addition, got {len(additions)}: {additions}"
        )

    def test_chat_model_passes_timeout_to_both_impls(self):
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_client_timeout_fix(_cycle8_diagnosis())
        }
        cm = files["client_timeout_chat_model.py"].content
        # Reads the env var with the 21600s default (the one stated edit).
        assert 'os.getenv("FIVE_REQUEST_TIMEOUT", "21600")' in cm
        # The explicit timeout is passed to BOTH impls (fast + large). Counted
        # over the BODY only: the derive header legitimately echoes the stated
        # instruction (target + replacement), so a raw substring count over the
        # whole file would double-count.
        impl_lines = [
            ln
            for ln in cm.splitlines()
            if "_ChatCompletionsText(" in ln and "import" not in ln
        ]
        assert len(impl_lines) == 2
        assert all("timeout=request_timeout" in ln for ln in impl_lines)
        assert "fast_impl = _ChatCompletionsText(" in cm
        assert "large_impl = _ChatCompletionsText(" in cm

    def test_driver_exports_timeout_ge_outer_wall_and_repoints(self):
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_client_timeout_fix(_cycle8_diagnosis())
        }
        driver = files["client_timeout_driver.sh"].content
        # Exports FIVE_REQUEST_TIMEOUT >= the 10800s outer wall.
        m = re.search(r"export FIVE_REQUEST_TIMEOUT=(\d+)", driver)
        assert m is not None
        assert int(m.group(1)) >= 10800
        # Repoints RUN/SPOKE at the new files.
        assert "RUN=/home/sasha/Research/four/run-v3.py" in driver
        assert (
            "SPOKE=/home/sasha/Research/four/examples/spokes/cycle-implementation-v4.py"
            in driver
        )

    def test_propose_yields_client_timeout_path(self):
        p = propose(_cycle8_diagnosis())
        assert len(p.new_files) == 4
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in p.new_files)


# ---------------------------------------------------------------------------
# Cycle-11 (inner-wall) replay
# ---------------------------------------------------------------------------

_PREDECESSOR_DRIVER_TEXT = (
    "#!/bin/bash\n"
    "export FIVE_MODEL=fast-qwen\n"
    "export FIVE_LARGE_MODEL=qwen\n"
    "--inner-seconds 2400\n"
    "run_cycle\n"
)


def _write_predecessor(tmp_path: Path, text: str = _PREDECESSOR_DRIVER_TEXT) -> str:
    """Write the predecessor driver to a temp file; return its path as str."""
    p = tmp_path / "predecessor_driver.sh"
    p.write_text(text, encoding="utf-8")
    return str(p)


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
    def test_emits_one_new_file(self, tmp_path: Path):
        pred = _write_predecessor(tmp_path)
        files = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred)
        assert len(files) == 1
        assert files[0].path.startswith(PROPOSAL_NAMESPACE)

    def test_only_delta_is_inner_seconds(self, tmp_path: Path):
        pred = _write_predecessor(tmp_path)
        f = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred)[0]
        content = f.content
        # The corrected inner wall: heaviest (2400) + margin (1800) = 4200.
        assert "--inner-seconds 4200" in content
        # The old value is gone from the driver body (single substitution).
        # (It may appear quoted in the diff-statement header — that is expected.)
        assert "\n--inner-seconds 2400\n" not in content
        # Everything else from the predecessor is byte-identical.
        for line in (
            "export FIVE_MODEL=fast-qwen",
            "export FIVE_LARGE_MODEL=qwen",
            "run_cycle",
        ):
            assert line in content

    def test_diff_isolation(self, tmp_path: Path):
        """Difflib diff vs predecessor == exactly the stated --inner-seconds line."""
        pred_text = _PREDECESSOR_DRIVER_TEXT
        pred = _write_predecessor(tmp_path)
        f = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred)[0]
        # The predecessor is a .sh file, so the derive header uses # comments.
        gen_body = _strip_derive_header(f.content, is_py=False)
        pred_lines = pred_text.splitlines(keepends=True)
        gen_lines = gen_body.splitlines(keepends=True)
        diff = list(difflib.unified_diff(pred_lines, gen_lines, n=0))
        deletions = [ln for ln in diff if ln.startswith("-") and not ln.startswith("---")]
        additions = [ln for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
        assert len(deletions) == 1, (
            f"expected 1 deletion, got {len(deletions)}: {deletions}"
        )
        assert len(additions) == 1, (
            f"expected 1 addition, got {len(additions)}: {additions}"
        )
        # The deleted line is the old --inner-seconds; the added line is the new.
        assert "--inner-seconds 2400" in deletions[0]
        assert "--inner-seconds 4200" in additions[0]

    def test_margin_over_old_when_no_heaviest(self, tmp_path: Path):
        d = Diagnosis(
            failure_mode="inner-wall",
            inner_wall_kill_cycle=11,
            inner_seconds=3000,
            source="sentry-report",
        )
        # Predecessor must carry the old value (3000) for the target to match.
        pred_text = (
            "#!/bin/bash\n"
            "export FIVE_MODEL=fast-qwen\n"
            "export FIVE_LARGE_MODEL=qwen\n"
            "--inner-seconds 3000\n"
            "run_cycle\n"
        )
        pred = _write_predecessor(tmp_path, text=pred_text)
        f = build_inner_wall_fix(d, predecessor_driver=pred)[0]
        # Old inner wall (3000) + margin (1800) = 4800.
        assert "--inner-seconds 4800" in f.content
        assert "\n--inner-seconds 3000\n" not in f.content

    def test_fails_loud_when_token_absent(self, tmp_path: Path):
        """Derive-by-reference fails loud when the target line is not in the predecessor."""
        from revolver.derive import DerivationError

        d = _cycle11_diagnosis()
        pre = "#!/bin/bash\nexport FIVE_MODEL=fast-qwen\nrun_cycle\n"
        pred = _write_predecessor(tmp_path, text=pre)
        with pytest.raises(DerivationError, match="matched 0 line"):
            build_inner_wall_fix(d, predecessor_driver=pred)


# ---------------------------------------------------------------------------
# Cycle-16 (outer-freshness) replay: poisoning vs guard
# ---------------------------------------------------------------------------
#
# DETERMINISTIC, no endpoints, no wall-clocks. We seed a stale trajectory
# (exit:task_complete) + an inner stub that dies rc=124 with EMPTY output, then
# assert:
#   * the run-v3-shaped reader (the predecessor's "read the newest .json")
#     reproduces the POISONING - it accepts the stale DONE as completion;
#   * the run-v4-shaped reader (the generated pass-freshness guard) RE-INVOKES -
#     it never accepts the stale file as completion.
#
# The v4 reader is exercised by EXECUTING the guard functions out of the
# GENERATED run-v4 content (exec into a namespace), so the test validates the
# actual generated code, not a re-implementation.


def _cycle16_diagnosis() -> Diagnosis:
    """A fixed cycle-16 outer-freshness diagnosis (pure, no sentry import)."""
    return Diagnosis(
        failure_mode="outer-freshness",
        no_new_trajectory_witnessed=True,
        pass_start_max_seq=26,
        outer_wall=10800,
        endpoint_pin="standard (.157:8080 fast-qwen / .161:8081 qwen)",
        source="sentry-report",
        evidence="cycle 14/15 unwitnessed inner death (rc=124 EMPTY)",
    )


def _seed_stale_trajectory(tmp_path, seq: int = 26) -> Path:
    """Seed a PRIOR cycle's exit:task_complete trajectory (the stale file)."""
    import json

    traj_dir = tmp_path / "trajectories"
    traj_dir.mkdir(parents=True, exist_ok=True)
    stale = traj_dir / f"trajectory_{seq:04d}.json"
    stale.write_text(
        json.dumps(
            {
                "outcome": "exit:task_complete",
                "messages": [
                    {"role": "assistant", "content": "DONE"},
                ],
            }
        )
    )
    return traj_dir


def _v3_read_newest(trajectories_dir: Path) -> str:
    """The predecessor's step-2 read (run-v3.py:84): the newest .json, unguarded.

    This is the POISONING path: it globs the newest .json and reads its outcome
    with NO branch for "nothing new this pass".
    """
    import glob
    import json

    p = sorted(glob.glob(str(trajectories_dir / "*.json")))[-1]
    return json.load(open(p)).get("outcome", "?")


def _v4_guard_namespace() -> dict:
    """Exec the GENERATED run-v4 content into a namespace (validates real code)."""
    files = {
        f.path.rsplit("/", 1)[-1]: f
        for f in build_outer_freshness_fix(_cycle16_diagnosis(), predecessor_runner="PRE")
    }
    runner = files["outer_freshness_run_v4.py"].content
    ns: dict = {}
    exec(compile(runner, "outer_freshness_run_v4.py", "exec"), ns)
    return ns


class TestOuterFreshnessReplay:
    def test_emits_two_new_files(self):
        files = build_outer_freshness_fix(
            _cycle16_diagnosis(), predecessor_runner="PRE"
        )
        assert len(files) == 2
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in files)

    def test_all_py_files_compile(self):
        """Every generated .py file is syntactically valid Python (py_compile)."""
        for f in build_outer_freshness_fix(
            _cycle16_diagnosis(), predecessor_runner="PRE"
        ):
            if f.path.endswith(".py"):
                with tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w", delete=False, encoding="utf-8"
                ) as tmp:
                    tmp.write(f.content)
                    tmp_path = tmp.name
                try:
                    py_compile.compile(tmp_path, doraise=True)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

    def test_import_resolution(self, tmp_path: Path):
        """Exec the generated runner in a namespace — proves the emitted code
        is real, importable Python (not a re-typed body)."""
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_outer_freshness_fix(
                _cycle16_diagnosis(), predecessor_runner="PRE"
            )
        }
        runner = files["outer_freshness_run_v4.py"].content
        # Compile and exec into a namespace — if the code has syntax errors
        # or unresolvable imports at module level, this will raise.
        ns: dict = {}
        exec(compile(runner, "outer_freshness_run_v4.py", "exec"), ns)
        # The guard function must be present and callable.
        assert "pass_freshness_guard" in ns
        assert callable(ns["pass_freshness_guard"])

    def test_diff_isolation(self):
        """For the generated runner, verify structural invariants of the
        full-rewrite derivation (not a 1-line diff)."""
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_outer_freshness_fix(
                _cycle16_diagnosis(), predecessor_runner="PRE"
            )
        }
        runner = files["outer_freshness_run_v4.py"].content
        # The runner is a full rewrite (not a line-substitution), so we verify
        # structural invariants instead of a 1-line diff:
        # 1. It compiles.
        compile(runner, "outer_freshness_run_v4.py", "exec")
        # 2. It contains the guard function.
        assert "def pass_freshness_guard" in runner
        # 3. It contains the DEAD-UNWITNESSED sentinel.
        assert "DEAD-UNWITNESSED" in runner
        # 4. It exits 124 on stale.
        assert "sys.exit(124)" in runner

    def test_v3_reader_reproduces_poisoning(self, tmp_path):
        """The v3-shaped reader accepts the stale DONE as completion (the bug)."""
        traj_dir = _seed_stale_trajectory(tmp_path)
        # The v3 reader globs the newest .json and reads its outcome - it sees the
        # stale exit:task_complete and would accept completion.
        outcome = _v3_read_newest(traj_dir)
        assert outcome == "exit:task_complete"

    def test_v4_reader_reinvokes_on_stale(self, tmp_path):
        """The v4-shaped guard RE-INVOKES: the stale file is never completion."""
        traj_dir = _seed_stale_trajectory(tmp_path, seq=26)
        ns = _v4_guard_namespace()
        guard = ns["pass_freshness_guard"]
        # pass_start_max_seq=26 (the pass-start snapshot). The newest trajectory is
        # seq 26 (the stale file) - NOT newer than the snapshot.
        assert guard(str(traj_dir), 26) is False
        # => dead-unwitnessed => the generated main() would re-invoke (sys.exit(124)).
        runner = build_outer_freshness_fix(
            _cycle16_diagnosis(), predecessor_runner="PRE"
        )[0].content
        assert "DEAD-UNWITNESSED" in runner
        assert "sys.exit(124)" in runner

    def test_v4_reader_accepts_when_newer(self, tmp_path):
        """When a NEWER trajectory exists, the guard passes (normal completion)."""
        traj_dir = _seed_stale_trajectory(tmp_path, seq=26)
        import json

        # Seed a NEWER trajectory (seq 27) - this pass's real witness.
        (traj_dir / "trajectory_0027.json").write_text(
            json.dumps({"outcome": "exit:task_complete", "messages": []})
        )
        ns = _v4_guard_namespace()
        guard = ns["pass_freshness_guard"]
        assert guard(str(traj_dir), 26) is True

    def test_generated_runner_is_valid_python(self):
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_outer_freshness_fix(
                _cycle16_diagnosis(), predecessor_runner="PRE"
            )
        }
        runner = files["outer_freshness_run_v4.py"].content
        compile(runner, "outer_freshness_run_v4.py", "exec")

    def test_driver_repoints_run_and_exports_timeout(self):
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_outer_freshness_fix(
                _cycle16_diagnosis(), predecessor_runner="PRE"
            )
        }
        driver = files["outer_freshness_driver.sh"].content
        # RUN repointed at the generated run-v4 runner.
        assert "RUN=revolver/fixes/outer_freshness_run_v4.py" in driver
        # Exports FIVE_REQUEST_TIMEOUT >= the 10800s outer wall.
        m = re.search(r"export FIVE_REQUEST_TIMEOUT=(\d+)", driver)
        assert m is not None
        assert int(m.group(1)) >= 10800
        # Endpoint pins verbatim.
        for tok in (
            "FIVE_BASE_URL",
            "FIVE_MODEL",
            "FIVE_LARGE_URL",
            "FIVE_LARGE_MODEL",
            "FIVE_MAX_TOKENS",
        ):
            assert tok in driver

    def test_proposal_validates_additions_only(self):
        """The generated files pass the existing additive-path validation."""
        from revolver.proposal import RepairProposal
        from revolver.validation import check_imports, check_syntax

        files = build_outer_freshness_fix(
            _cycle16_diagnosis(), predecessor_runner="PRE"
        )
        proposal = RepairProposal(
            pipeline_id="revolver",
            diagnosis=_cycle16_diagnosis(),
            new_files=files,
        )
        # Hard rule 7: additions only (all under PROPOSAL_NAMESPACE).
        proposal.validate()
        # Content validation: syntax + imports on every generated file.
        for nf in files:
            assert check_syntax(nf.content, path=nf.path).ok
            if nf.path.endswith(".py"):
                assert check_imports(nf.content, path=nf.path).ok


# ---------------------------------------------------------------------------
# Negative test: broken instruction fails at derive time
# ---------------------------------------------------------------------------


class TestBrokenInstructionFails:
    def test_broken_instruction_fails_at_derive(self, tmp_path: Path):
        """A deliberately broken instruction (wrong target text) makes the
        proposal fail at derive time; the test proves it raises."""
        from revolver.derive import DerivationError

        # Use the inner-wall builder with a predecessor that does NOT contain
        # the expected target line. The builder will emit an instruction whose
        # target line is absent from the predecessor → derive() raises.
        d = Diagnosis(
            failure_mode="inner-wall",
            inner_wall_kill_cycle=11,
            inner_seconds=2400,
            source="sentry-report",
        )
        # Predecessor with a DIFFERENT inner-seconds value than the diagnosis
        # expects (the builder targets the diagnosis's value, not the file's).
        pred_text = (
            "#!/bin/bash\n"
            "export FIVE_MODEL=fast-qwen\n"
            "export FIVE_LARGE_MODEL=qwen\n"
            "--inner-seconds 9999\n"
            "run_cycle\n"
        )
        pred = _write_predecessor(tmp_path, text=pred_text)
        with pytest.raises(DerivationError):
            build_inner_wall_fix(d, predecessor_driver=pred)


# ---------------------------------------------------------------------------
# Helper: strip the derive header from generated content
# ---------------------------------------------------------------------------


def _strip_derive_header(content: str, *, is_py: bool) -> str:
    """Remove the derive() header from generated content to expose the pure body.

    For .py files the header is a triple-quoted docstring.
    For .sh files the header is a block of # comment lines.
    """
    lines = content.splitlines(keepends=True)
    if not lines:
        return content

    if is_py:
        # The header starts with a docstring (""") and ends at the closing """.
        if lines[0].lstrip().startswith('"""'):
            for i in range(1, len(lines)):
                if '"""' in lines[i]:
                    return "".join(lines[i + 1 :])
            # Single-line docstring (unlikely but handle it).
            return "".join(lines[1:])
        return content
    else:
        # For .sh files, the header is a block of # comment lines at the top.
        # Find the first non-comment, non-empty line.
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped and not stripped.startswith("#"):
                return "".join(lines[i:])
        # All comments (unlikely).
        return content


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
