"""revolver.derive — derive-by-reference: predecessor-in, versioned-variant-out.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: Build Order row "Derive-by-reference | 17-19" + TICKET-076. This is the
core of the derive-by-reference procedure that replaces value-embedding generators:
read a predecessor READ-ONLY, apply EXACTLY ONE stated minimal edit, and emit a NEW
versioned file whose docstring names the predecessor by PATH (the version chain:
run-vN names run-v(N-1), which names its own predecessor). The predecessor is never
mutated (hard rule 7).

Verification is BY CONSTRUCTION and fails loud: the output must (a) compile
(``py_compile`` for ``.py``) and (b) differ from the predecessor by EXACTLY the
stated lines (the docstring header + the one edit). Any extra delta is a
:class:`DerivationError` — the proposal fails, nothing stages.

Pure function of its inputs: deterministic, stdlib-only, no endpoints, no
wall-clocks. The only I/O is reading the predecessor (through an overridable seam)
and a transient temp-file compile check (also overridable).
"""

from __future__ import annotations

import difflib
import py_compile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class DerivationError(Exception):
    """Raised when a derivation cannot be verified by construction.

    Triggered by an ambiguous target (matches != 1 line), an output that does not
    compile, or an output whose diff against the predecessor is not exactly the
    stated lines. The proposal fails loud; nothing is staged.
    """


@dataclass(frozen=True)
class ChangeInstruction:
    """One stated minimal edit — DATA, not code.

    The scar table becomes a vocabulary the machine composes: each fix class is a
    set of these instructions, each naming a predecessor by path (resolved
    separately) and a single edit to apply.

    Attributes:
        kind: The edit kind (e.g. ``swap-import``, ``insert-export``,
            ``repoint-path``).
        target: The exact line to match (whole-line, trailing whitespace ignored).
            Must match exactly ONE line in the predecessor.
        replacement: The exact new text that replaces the target line (may be
            multi-line; for an insert, re-include the anchor line first).
        new_name: The versioned output filename (hard-rule-7 convention).
        evidence: The citation string motivating the edit.
    """

    kind: str
    target: str
    replacement: str
    new_name: str
    evidence: str


@dataclass
class DerivedVariant:
    """A NEW versioned file derived from a predecessor by one stated edit.

    Attributes:
        path: The versioned output filename (``instruction.new_name``).
        content: The full derived text (docstring header + edited body).
        predecessor: The predecessor's PATH (a reference, never its body).
        instruction: The :class:`ChangeInstruction` that produced it.
        diff_from_predecessor: The stated one-edit diff statement.
        evidence: The citation string.
    """

    path: str
    content: str
    predecessor: str
    instruction: ChangeInstruction
    diff_from_predecessor: str
    evidence: str


def _diff_statement(instruction: ChangeInstruction) -> str:
    """The single-line diff-from-predecessor statement for the docstring."""
    return (
        f"ONE edit ({instruction.kind}): replace the line "
        f"{instruction.target!r} with {instruction.replacement!r}"
    )


def _header_lines(instruction: ChangeInstruction, pred_path: Path) -> list[str]:
    """The deterministic docstring/comment header naming the predecessor by path."""
    diff_stmt = _diff_statement(instruction)
    q = '"""'
    if instruction.new_name.endswith(".py"):
        first = (
            f'{q}{instruction.new_name} — derived from {pred_path} '
            f"(predecessor left unchanged; hard rule 7: never mutate)."
        )
        return [
            first,
            "",
            f"Diff from predecessor: {diff_stmt}",
            f"Evidence: {instruction.evidence}",
            q,
        ]
    first = (
        f"# {instruction.new_name} — derived from {pred_path} "
        f"(predecessor left unchanged; hard rule 7: never mutate)."
    )
    return [
        first,
        f"# Diff from predecessor: {diff_stmt}",
        f"# Evidence: {instruction.evidence}",
    ]


def _changed_lines(old_lines: list[str], new_lines: list[str]) -> tuple[list[str], list[str]]:
    """Return (deleted, added) line lists from a difflib diff (order-preserving)."""
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    deleted: list[str] = []
    added: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            deleted.extend(old_lines[i1:i2])
        if tag in ("insert", "replace"):
            added.extend(new_lines[j1:j2])
    return deleted, added


def _default_compile_check(content: str, new_name: str) -> None:
    """py_compile the output for ``.py`` (transient temp file); no-op otherwise."""
    if not new_name.endswith(".py"):
        return
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / new_name
        path.write_text(content, encoding="utf-8")
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            raise DerivationError(
                f"derived output does not compile: {exc.msg}"
            ) from exc


def derive(
    predecessor: Path | str,
    instruction: ChangeInstruction,
    *,
    read_text: Callable[[Path], str] | None = None,
    compile_check: Callable[[str, str], None] | None = None,
) -> DerivedVariant:
    """Derive a NEW versioned file from a predecessor by ONE stated edit.

    Reads the predecessor READ-ONLY, applies exactly one minimal edit (the
    instruction's ``target`` line -> ``replacement``), and emits a NEW versioned
    file whose docstring names the predecessor by path. Verification by
    construction (fail loud): the output must compile (``.py``) and its diff
    against the predecessor must be EXACTLY the stated lines (header + edit).

    Args:
        predecessor: Path to the predecessor file (read-only reference).
        instruction: The single stated edit to apply.
        read_text: Overridable seam for reading the predecessor (default: real
            file read). Lets tests inject content without touching the real
            triple.
        compile_check: Overridable seam for the compile check (default:
            ``py_compile`` on a temp file for ``.py``).

    Raises:
        DerivationError: If the target matches != 1 line, the output does not
            compile, or the diff is not exactly the stated lines.
    """
    pred_path = Path(predecessor)
    text = read_text(pred_path) if read_text is not None else pred_path.read_text(encoding="utf-8")
    pred_lines = text.splitlines()

    # Exactly ONE target line (ambiguity is loud).
    matches = [
        i for i, line in enumerate(pred_lines) if line.rstrip() == instruction.target.rstrip()
    ]
    if len(matches) != 1:
        raise DerivationError(
            f"target {instruction.target!r} matched {len(matches)} line(s) in "
            f"{pred_path} (need exactly 1)"
        )
    idx = matches[0]
    target_line = pred_lines[idx]
    replacement_lines = instruction.replacement.splitlines()

    # Apply the single edit (never mutate the predecessor — build a new list).
    edited_body = pred_lines[:idx] + replacement_lines + pred_lines[idx + 1 :]
    header_lines = _header_lines(instruction, pred_path)
    output_lines = header_lines + edited_body
    output_content = "\n".join(output_lines) + "\n"

    # Verification by construction (fail loud, before any output is returned).
    check = compile_check if compile_check is not None else _default_compile_check
    check(output_content, instruction.new_name)
    deleted, added = _changed_lines(pred_lines, output_lines)
    expected_deleted = [target_line]
    expected_added = list(header_lines) + list(replacement_lines)
    if deleted != expected_deleted or added != expected_added:
        raise DerivationError(
            "derived output has an extra delta beyond the stated edit: "
            f"deleted={deleted!r} added={added!r} "
            f"(expected deleted={expected_deleted!r} added={expected_added!r})"
        )

    return DerivedVariant(
        path=instruction.new_name,
        content=output_content,
        predecessor=str(pred_path),
        instruction=instruction,
        diff_from_predecessor=_diff_statement(instruction),
        evidence=instruction.evidence,
    )
