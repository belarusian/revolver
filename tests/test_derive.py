"""tests/test_derive.py — derive-by-reference core: verification by construction.

Diff from predecessor: NEW test module (no predecessor in this repo).
Evidence: TICKET-076. The derive core reads a predecessor READ-ONLY, applies ONE
stated minimal edit, and emits a NEW versioned file whose docstring names the
predecessor by path. Verification by construction fails loud: the output must
compile and its diff must be EXACTLY the stated lines. Tests use temp-dir
fixtures (a 10-line stub runner) — they do NOT read the real triple.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from revolver.derive import ChangeInstruction, DerivedVariant, DerivationError, derive

# A 10-line stub runner predecessor (the tests never read the real triple).
_STUB = (
    "#!/usr/bin/env python3\n"
    "import argparse\n"
    "import os\n"
    "import sys\n"
    "\n"
    "from four.core import run, save_trajectory\n"
    "from four.chat_model import context_aware_invoke\n"
    "from four.parse import robust_parse\n"
    "\n"
    "def main():\n"
    "    pass\n"
)


def _write_stub(tmp_path: Path, name: str = "run-v2.py") -> Path:
    pred = tmp_path / name
    pred.write_text(_STUB, encoding="utf-8")
    return pred


def _swap_import() -> ChangeInstruction:
    return ChangeInstruction(
        kind="swap-import",
        target="from four.chat_model import context_aware_invoke",
        replacement="from four.chat_model_v2 import context_aware_invoke",
        new_name="run-v3.py",
        evidence="sentry cycle 8 (2026-08-25)",
    )


def _body(content: str) -> str:
    """The file body after the docstring (the docstring quotes the target line)."""
    return content.split('"""', 2)[2]


class TestDeriveSwapImport:
    def test_output_compiles_and_diff_is_stated_lines(self, tmp_path: Path):
        pred = _write_stub(tmp_path)
        variant = derive(pred, _swap_import())
        assert isinstance(variant, DerivedVariant)
        assert variant.path == "run-v3.py"
        # The stated import swap is present in the BODY (the docstring quotes the
        # target line, so assert on the body, not the whole content).
        body = _body(variant.content)
        assert "from four.chat_model_v2 import context_aware_invoke" in body
        assert "from four.chat_model import context_aware_invoke" not in body

    def test_docstring_names_predecessor_by_path(self, tmp_path: Path):
        pred = _write_stub(tmp_path)
        variant = derive(pred, _swap_import())
        # The docstring carries the predecessor's PATH (a reference).
        assert str(pred) in variant.content
        # And the stated diff + the evidence.
        assert "Diff from predecessor:" in variant.content
        assert "swap-import" in variant.content
        assert "sentry cycle 8 (2026-08-25)" in variant.content

    def test_predecessor_is_not_mutated(self, tmp_path: Path):
        pred = _write_stub(tmp_path)
        before = pred.read_text(encoding="utf-8")
        derive(pred, _swap_import())
        # Hard rule 7: the predecessor is byte-identical after the derive.
        assert pred.read_text(encoding="utf-8") == before

    def test_read_text_seam_injects_content(self, tmp_path: Path):
        # The read_text seam lets a caller inject predecessor content (resolve()
        # is faked — no real triple read).
        pred = tmp_path / "run-v2.py"  # not written to disk
        variant = derive(pred, _swap_import(), read_text=lambda p: _STUB)
        assert variant.path == "run-v3.py"
        assert "from four.chat_model_v2 import context_aware_invoke" in _body(variant.content)

    def test_deterministic(self, tmp_path: Path):
        pred = _write_stub(tmp_path)
        a = derive(pred, _swap_import())
        b = derive(pred, _swap_import())
        assert a.content == b.content
        assert a.predecessor == b.predecessor


class TestDeriveFailLoud:
    def test_ambiguous_target_raises(self, tmp_path: Path):
        # A target matching 2 lines is ambiguous -> DerivationError.
        pred = _write_stub(tmp_path)
        pred.write_text(_STUB.replace("import os\n", "import os\nimport os\n"), encoding="utf-8")
        instr = ChangeInstruction(
            kind="swap-import",
            target="import os",
            replacement="import os",
            new_name="run-v3.py",
            evidence="e",
        )
        with pytest.raises(DerivationError, match="matched 2"):
            derive(pred, instr)

    def test_no_target_match_raises(self, tmp_path: Path):
        pred = _write_stub(tmp_path)
        instr = ChangeInstruction(
            kind="swap-import",
            target="from four.nonexistent import thing",
            replacement="x",
            new_name="run-v3.py",
            evidence="e",
        )
        with pytest.raises(DerivationError, match="matched 0"):
            derive(pred, instr)

    def test_noop_replacement_extra_delta_raises(self, tmp_path: Path):
        # A "bad replacement" that is a no-op (replacement == target) leaves the
        # body unchanged, so the diff is header-only — NOT the stated edit. The
        # verification-by-construction guard fails loud (extra delta).
        pred = _write_stub(tmp_path)
        instr = ChangeInstruction(
            kind="swap-import",
            target="from four.chat_model import context_aware_invoke",
            replacement="from four.chat_model import context_aware_invoke",  # no-op
            new_name="run-v3.py",
            evidence="e",
        )
        with pytest.raises(DerivationError, match="extra delta"):
            derive(pred, instr)

    def test_compile_failure_raises(self, tmp_path: Path):
        # A replacement that breaks the Python syntax -> compile check fails.
        pred = _write_stub(tmp_path)
        instr = ChangeInstruction(
            kind="swap-import",
            target="from four.chat_model import context_aware_invoke",
            replacement="def broken(:",  # syntax error
            new_name="run-v3.py",
            evidence="e",
        )
        with pytest.raises(DerivationError, match="does not compile"):
            derive(pred, instr)


class TestDeriveNonPython:
    def test_shell_driver_diff_is_stated_lines(self, tmp_path: Path):
        # A .sh predecessor: the header is # comments, no compile check.
        driver = (
            "#!/bin/bash\n"
            "set -uo pipefail\n"
            "RUN=/home/sasha/Research/four/run-v3.py\n"
            "SPOKE=/home/sasha/Research/four/examples/spokes/cycle-implementation-v4.py\n"
            "export FIVE_REQUEST_TIMEOUT=21600\n"
        )
        pred = tmp_path / "run-cycles-v3.sh"
        pred.write_text(driver, encoding="utf-8")
        instr = ChangeInstruction(
            kind="repoint-path",
            target="RUN=/home/sasha/Research/four/run-v3.py",
            replacement="RUN=/home/sasha/Research/four/run-v4.py",
            new_name="run-cycles-v4.sh",
            evidence="trajectory_0027/0029",
        )
        variant = derive(pred, instr)
        assert variant.path == "run-cycles-v4.sh"
        # The body (after the # comment header) carries the new RUN and not the old.
        body = variant.content.split("\n", 3)[3]
        assert "RUN=/home/sasha/Research/four/run-v4.py" in body
        assert "RUN=/home/sasha/Research/four/run-v3.py" not in body
        # The # comment header names the predecessor by path + the stated diff.
        assert str(pred) in variant.content
        assert "# Diff from predecessor:" in variant.content
