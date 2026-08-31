"""tests/test_fixes_generators.py — structural-contract unit tests for the two founding fix generators.

Diff from predecessor: NEW test module (no predecessor in this repo).
Evidence: TICKET-086/088/089 — a dedicated structural-contract unit-test module for
``build_client_timeout_fix`` and ``build_inner_wall_fix`` (distinct from the replay
*acceptance* tests in ``tests/test_replay.py``, which assert semantic equivalence to
the golden reference and are execution-plane-dependent).

These tests assert the STRUCTURAL CONTRACT, not golden-reference equivalence:

  * file count (4 / 1) and every path under ``PROPOSAL_NAMESPACE``;
  * every ``NewFile.content`` embeds both ``"Diff from predecessor:"`` and
    ``"Evidence:"`` (the house docstring contract — TICKET-089);
  * client-timeout: the chat-model passes ``timeout=request_timeout`` to BOTH impls
    (fast + large); the runner and spoke each carry exactly the one-line import
    annotation delta; the driver exports ``FIVE_REQUEST_TIMEOUT`` >= its outer wall
    and the ``RUN=``/``SPOKE=`` lines are present;
  * inner-wall: exactly ONE new file; the ONLY delta vs the predecessor driver text is
    the ``--inner-seconds`` value (everything else byte-identical); the new value is
    ``heaviest_inner_duration + margin`` when present, else ``inner_seconds + margin``,
    else ``default + margin``;
  * both builders are pure + deterministic (same input -> identical output across two
    calls — TICKET-088);
  * client-timeout is registered in ``FIX_BUILDERS`` and reachable via ``propose()``;
    inner-wall is called directly with a keyword-only ``predecessor_driver`` and is
    intentionally NOT in the single-arg ``FIX_BUILDERS`` registry (TICKET-087 — the
    documented fact is asserted, not changed).

Client-timeout tests that read the real triple dir are guarded with ``@requires_triple``
(like ``test_replay.py``). Inner-wall tests write a temp predecessor driver file (like
``test_replay.py``'s ``_write_predecessor``) and are pure (no triple dir required).
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import pytest

from revolver.diagnosis import Diagnosis
from revolver.fixes import (
    FIX_BUILDERS,
    _DEFAULT_INNER_SECONDS,
    _INNER_WALL_MARGIN,
    build_client_timeout_fix,
    build_inner_wall_fix,
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
# Helpers: strip the derive header / opcode-based change counting
# ---------------------------------------------------------------------------


def _changed_lines(
    pred_lines: list[str], gen_lines: list[str]
) -> tuple[list[str], list[str]]:
    """(deleted, added) lines between predecessor and derived body.

    Uses SequenceMatcher opcodes, NOT unified_diff prefix parsing: a content
    line like '--inner-seconds 2400' renders as '---inner-seconds 2400' in a
    unified diff and is indistinguishable from a file header by prefix alone.
    Opcodes classify by structure, not by string shape.
    """
    sm = difflib.SequenceMatcher(None, pred_lines, gen_lines)
    deleted: list[str] = []
    added: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            deleted.extend(pred_lines[i1:i2])
        if tag in ("replace", "insert"):
            added.extend(gen_lines[j1:j2])
    return deleted, added


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
        # For .sh files, the derive header is a block of "# "-prefixed comment
        # lines. The shebang (#!) is NOT a header line — it terminates the
        # header and belongs to the body (the predecessor starts with it).
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped.startswith("# ") or stripped == "#":
                continue
            return "".join(lines[i:])
        # All header (unlikely).
        return content


# ---------------------------------------------------------------------------
# Cycle-8 (client-timeout) structural contract
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


@requires_triple
class TestClientTimeoutContract:
    """Structural contract for ``build_client_timeout_fix`` (reads the real triple dir)."""

    def test_emits_exactly_four_new_files(self):
        files = build_client_timeout_fix(_cycle8_diagnosis())
        assert len(files) == 4

    def test_all_paths_under_proposal_namespace(self):
        files = build_client_timeout_fix(_cycle8_diagnosis())
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in files)

    def test_every_content_embeds_docstring_contract(self):
        """TICKET-089: every generated file's content embeds both markers."""
        for f in build_client_timeout_fix(_cycle8_diagnosis()):
            assert "Diff from predecessor:" in f.content, f.path
            assert "Evidence:" in f.content, f.path

    def test_chat_model_passes_timeout_to_both_impls(self):
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_client_timeout_fix(_cycle8_diagnosis())
        }
        cm = files["client_timeout_chat_model.py"].content
        # Reads the env var with the 21600s default (the one stated edit).
        assert 'os.getenv("FIVE_REQUEST_TIMEOUT", "21600")' in cm
        # The explicit timeout is passed to BOTH impls (fast + large). Counted
        # over the whole file: the derive header legitimately echoes the stated
        # instruction (target + replacement) but never names _ChatCompletionsText,
        # so the only matches are the two body impl lines.
        impl_lines = [
            ln
            for ln in cm.splitlines()
            if "_ChatCompletionsText(" in ln and "import" not in ln
        ]
        assert len(impl_lines) == 2
        assert all("timeout=request_timeout" in ln for ln in impl_lines)
        assert "fast_impl = _ChatCompletionsText(" in cm
        assert "large_impl = _ChatCompletionsText(" in cm

    def test_runner_and_spoke_carry_one_line_import_delta(self):
        """TICKET-086: the runner AND the spoke each carry exactly the one-line
        import annotation delta (not just the chat-model)."""
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_client_timeout_fix(_cycle8_diagnosis())
        }
        preds = {
            "client_timeout_runner.py": _TRIPLE_DIR / "run-v3.py",
            "client_timeout_spoke.py": _TRIPLE_DIR / "cycle-implementation-v4.py",
        }
        annotated = (
            "from four.chat_model_v2 import context_aware_invoke"
            "  # client-timeout: explicit request timeout"
        )
        for name, pred_path in preds.items():
            content = files[name].content
            # The annotated import line is present.
            assert annotated in content, name
            # The ONLY body delta vs the predecessor is the one-line annotation:
            # exactly one line deleted (the unannotated import) and one added
            # (the annotated import); everything else is byte-identical.
            gen_body = _strip_derive_header(content, is_py=True)
            pred_lines = pred_path.read_text(encoding="utf-8").splitlines(keepends=True)
            gen_lines = gen_body.splitlines(keepends=True)
            deletions, additions = _changed_lines(pred_lines, gen_lines)
            assert len(deletions) == 1, (name, deletions)
            assert len(additions) == 1, (name, additions)
            assert deletions[0].rstrip() == "from four.chat_model_v2 import context_aware_invoke"
            assert additions[0].rstrip() == annotated

    def test_driver_exports_timeout_ge_outer_wall_and_run_spoke_present(self):
        files = {
            f.path.rsplit("/", 1)[-1]: f
            for f in build_client_timeout_fix(_cycle8_diagnosis())
        }
        driver = files["client_timeout_driver.sh"].content
        # Exports FIVE_REQUEST_TIMEOUT >= the 10800s outer wall.
        m = re.search(r"export FIVE_REQUEST_TIMEOUT=(\d+)", driver)
        assert m is not None
        assert int(m.group(1)) >= 10800
        # The RUN= and SPOKE= lines are present (exactly one each).
        run_lines = [ln for ln in driver.splitlines() if ln.startswith("RUN=")]
        spoke_lines = [ln for ln in driver.splitlines() if ln.startswith("SPOKE=")]
        assert len(run_lines) == 1
        assert len(spoke_lines) == 1

    def test_pure_and_deterministic(self):
        """TICKET-088: same input -> identical output across two calls."""
        d = _cycle8_diagnosis()
        first = build_client_timeout_fix(d)
        second = build_client_timeout_fix(d)
        assert [f.to_dict() for f in first] == [f.to_dict() for f in second]

    def test_registered_in_fix_builders(self):
        assert "client-timeout" in FIX_BUILDERS
        assert FIX_BUILDERS["client-timeout"] is build_client_timeout_fix

    def test_reachable_via_propose(self):
        p = propose(_cycle8_diagnosis())
        assert len(p.new_files) == 4
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in p.new_files)


# ---------------------------------------------------------------------------
# Cycle-11 (inner-wall) structural contract
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


class TestInnerWallContract:
    """Structural contract for ``build_inner_wall_fix`` (pure; temp predecessor)."""

    def test_emits_exactly_one_new_file(self, tmp_path: Path):
        pred = _write_predecessor(tmp_path)
        files = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred)
        assert len(files) == 1

    def test_all_paths_under_proposal_namespace(self, tmp_path: Path):
        pred = _write_predecessor(tmp_path)
        files = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred)
        assert all(f.path.startswith(PROPOSAL_NAMESPACE) for f in files)

    def test_every_content_embeds_docstring_contract(self, tmp_path: Path):
        """TICKET-089: the single generated file's content embeds both markers."""
        pred = _write_predecessor(tmp_path)
        for f in build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred):
            assert "Diff from predecessor:" in f.content
            assert "Evidence:" in f.content

    def test_only_delta_is_inner_seconds(self, tmp_path: Path):
        """TICKET-086: the ONLY delta vs the predecessor is the --inner-seconds value."""
        pred_text = _PREDECESSOR_DRIVER_TEXT
        pred = _write_predecessor(tmp_path)
        f = build_inner_wall_fix(_cycle11_diagnosis(), predecessor_driver=pred)[0]
        # The corrected inner wall: heaviest (2400) + margin (1800) = 4200.
        assert f"--inner-seconds {2400 + _INNER_WALL_MARGIN}" in f.content
        # Everything else from the predecessor is byte-identical: the ONLY body
        # delta is one line deleted (the old value) and one added (the new value).
        gen_body = _strip_derive_header(f.content, is_py=False)
        pred_lines = pred_text.splitlines(keepends=True)
        gen_lines = gen_body.splitlines(keepends=True)
        deletions, additions = _changed_lines(pred_lines, gen_lines)
        assert len(deletions) == 1, deletions
        assert len(additions) == 1, additions
        assert deletions[0].rstrip() == "--inner-seconds 2400"
        assert additions[0].rstrip() == f"--inner-seconds {2400 + _INNER_WALL_MARGIN}"
        # The untouched predecessor lines survive verbatim.
        for line in ("export FIVE_MODEL=fast-qwen", "export FIVE_LARGE_MODEL=qwen", "run_cycle"):
            assert line in gen_body

    def test_new_value_heaviest_plus_margin_when_present(self, tmp_path: Path):
        """heaviest_inner_duration present -> new = heaviest + margin (inner_seconds ignored)."""
        d = Diagnosis(
            failure_mode="inner-wall",
            inner_wall_kill_cycle=11,
            heaviest_inner_duration=2400,
            inner_seconds=3000,  # present but must be IGNORED when heaviest is present
            source="sentry-report",
        )
        pred = _write_predecessor(tmp_path)  # carries --inner-seconds 2400
        f = build_inner_wall_fix(d, predecessor_driver=pred)[0]
        # heaviest (2400) + margin (1800) = 4200, NOT inner_seconds (3000) + margin.
        assert f"--inner-seconds {2400 + _INNER_WALL_MARGIN}" in f.content
        assert f"--inner-seconds {3000 + _INNER_WALL_MARGIN}" not in f.content

    def test_new_value_inner_seconds_plus_margin_when_no_heaviest(self, tmp_path: Path):
        """heaviest absent, inner_seconds present -> new = inner_seconds + margin."""
        d = Diagnosis(
            failure_mode="inner-wall",
            inner_wall_kill_cycle=11,
            inner_seconds=3000,
            source="sentry-report",
        )
        pred_text = (
            "#!/bin/bash\n"
            "export FIVE_MODEL=fast-qwen\n"
            "export FIVE_LARGE_MODEL=qwen\n"
            "--inner-seconds 3000\n"
            "run_cycle\n"
        )
        pred = _write_predecessor(tmp_path, text=pred_text)
        f = build_inner_wall_fix(d, predecessor_driver=pred)[0]
        # inner_seconds (3000) + margin (1800) = 4800.
        assert f"--inner-seconds {3000 + _INNER_WALL_MARGIN}" in f.content

    def test_new_value_default_plus_margin_when_neither(self, tmp_path: Path):
        """heaviest AND inner_seconds absent -> new = default + margin."""
        d = Diagnosis(
            failure_mode="inner-wall",
            inner_wall_kill_cycle=11,
            source="sentry-report",
        )
        pred_text = (
            "#!/bin/bash\n"
            "export FIVE_MODEL=fast-qwen\n"
            "export FIVE_LARGE_MODEL=qwen\n"
            f"--inner-seconds {_DEFAULT_INNER_SECONDS}\n"
            "run_cycle\n"
        )
        pred = _write_predecessor(tmp_path, text=pred_text)
        f = build_inner_wall_fix(d, predecessor_driver=pred)[0]
        # default (3000) + margin (1800) = 4800.
        assert f"--inner-seconds {_DEFAULT_INNER_SECONDS + _INNER_WALL_MARGIN}" in f.content

    def test_pure_and_deterministic(self, tmp_path: Path):
        """TICKET-088: same input -> identical output across two calls."""
        pred = _write_predecessor(tmp_path)
        d = _cycle11_diagnosis()
        first = build_inner_wall_fix(d, predecessor_driver=pred)
        second = build_inner_wall_fix(d, predecessor_driver=pred)
        assert [f.to_dict() for f in first] == [f.to_dict() for f in second]

    def test_not_in_fix_builders_registry(self):
        """TICKET-087 (documented fact, do not change): the inner-wall builder takes a
        keyword-only predecessor_driver, so it is intentionally NOT in the single-arg
        FIX_BUILDERS registry; it is called directly with the predecessor text."""
        assert "inner-wall" not in FIX_BUILDERS

    def test_called_directly_with_keyword_only_predecessor_driver(self, tmp_path: Path):
        """predecessor_driver is keyword-only: passing it positionally must fail."""
        pred = _write_predecessor(tmp_path)
        d = _cycle11_diagnosis()
        with pytest.raises(TypeError):
            build_inner_wall_fix(d, pred)  # type: ignore[call-arg]
        # And the keyword form works.
        files = build_inner_wall_fix(d, predecessor_driver=pred)
        assert len(files) == 1


class TestClientTimeoutTripleDirSeam:
    """TICKET-090: build_client_timeout_fix accepts an overridable triple_dir seam.

    These tests use a temp dir with minimal predecessor files — no real triple
    directory required. Deterministic, pure, no execution-plane dependency.
    """

    def test_triple_dir_seam_produces_four_new_files(self, tmp_path: Path):
        """Passing triple_dir=tmp_path produces 4 NewFiles without a real triple."""
        # Write the four predecessor files with the exact target strings.
        chat_model = tmp_path / "chat_model.py"
        chat_model.write_text(
            "import os\n"
            "\n"
            "def get_timeout():\n"
            "    request_timeout = 600  # litellm built-in default — the cycle-8 cancel-loop\n"
            "    return request_timeout\n",
            encoding="utf-8",
        )
        runner = tmp_path / "run-v3.py"
        runner.write_text(
            "from four.chat_model_v2 import context_aware_invoke\n"
            "\n"
            "def run():\n"
            "    pass\n",
            encoding="utf-8",
        )
        spoke = tmp_path / "cycle-implementation-v4.py"
        spoke.write_text(
            "from four.chat_model_v2 import context_aware_invoke\n"
            "\n"
            "def cycle():\n"
            "    pass\n",
            encoding="utf-8",
        )
        driver = tmp_path / "run-cycles-v3.sh"
        driver.write_text(
            "#!/bin/bash\n"
            "export FIVE_REQUEST_TIMEOUT=21600\n",
            encoding="utf-8",
        )

        d = Diagnosis(
            failure_mode="client-timeout",
            client_timeout_cycle=8,
            source="sentry-report",
            evidence="cancel-loop",
        )
        files = build_client_timeout_fix(d, triple_dir=tmp_path)
        assert len(files) == 4
        # All paths under the proposal namespace.
        for f in files:
            assert f.path.startswith(PROPOSAL_NAMESPACE)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
