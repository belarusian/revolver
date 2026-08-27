"""revolver.validation — pure, dry-run validation of proposal artifacts.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: the package contract (revolver/__init__.py) states that every generated
file is NEW and additions-only, and that validation is a later phase (cycles 6-7).
The manifest (revolver/manifest.py) already enforces *structural* invariants
(additions-only, launch-safe) but says nothing about the *content* of the NEW
files it carries. This module closes that gap: it statically checks each
``NewFile``'s content for (a) Python syntax validity and (b) imports that resolve
to neither the standard library nor the revolver package. It is pure, dry-run,
stdlib-only, and performs no I/O and no process launch — it operates on the
in-memory ``content`` strings already held by the manifest.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from revolver.manifest import ProposalManifest

# The top-level module names owned by the revolver package. Every import of a
# revolver submodule (e.g. ``import revolver.diagnosis``) has top-level name
# ``revolver``, so this single entry covers the whole package for the top-level
# import check. Used as the default ``known_modules``.
_DEFAULT_KNOWN_MODULES: frozenset[str] = frozenset({"revolver"})


@dataclass
class SyntaxReport:
    """Result of a static syntax check on one artifact's content.

    Attributes:
        path: The artifact's relative path (echoed for reporting).
        ok: True when the content is syntactically valid (or is not Python).
        error: The compile error message for a failing ``.py`` file; an
            informational note (``"not python"``) for non-Python files; empty
            for a passing ``.py`` file.
    """

    path: str
    ok: bool
    error: str = ""


@dataclass
class ImportReport:
    """Result of a static import check on one artifact's content.

    Attributes:
        path: The artifact's relative path (echoed for reporting).
        ok: True when no top-level import is unresolved.
        missing: Sorted top-level module names that are neither stdlib nor in the
            known-modules set.
    """

    path: str
    ok: bool
    missing: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Combined per-artifact validation result.

    Attributes:
        path: The artifact's relative path.
        syntax_ok: Whether the content passed the syntax check.
        imports_ok: Whether the content passed the import check.
        errors: Human-readable error strings (empty when fully valid).
    """

    path: str
    syntax_ok: bool
    imports_ok: bool
    errors: list[str] = field(default_factory=list)


def _is_python(path: str) -> bool:
    """True when ``path`` denotes a Python source file (``*.py``)."""
    return path.endswith(".py")


def check_syntax(content: str, *, path: str) -> SyntaxReport:
    """Statically check ``content`` for Python syntax validity.

    Pure and in-memory: ``compile()`` is called on the string (no file is read or
    written). A ``.py`` path must compile; any other path (e.g. ``*.out``) is
    treated as non-Python and reported ``ok`` with a ``"not python"`` note.

    Args:
        content: The artifact's text.
        path: The artifact's relative path (used to pick the rule and to label
            the compile error).

    Returns:
        A :class:`SyntaxReport`.
    """
    if not _is_python(path):
        return SyntaxReport(path=path, ok=True, error="not python")
    try:
        compile(content, path, "exec")
    except SyntaxError as exc:
        return SyntaxReport(path=path, ok=False, error=str(exc))
    return SyntaxReport(path=path, ok=True, error="")


def _top_level_imports(content: str) -> set[str]:
    """Return the set of top-level module names imported by ``content``.

    Parses ``content`` with :mod:`ast` and collects the top-level (first) segment
    of every absolute ``import`` / ``from ... import`` target. Relative imports
    (``from . import x``) are skipped — they resolve within the current package,
    not to an external top-level module. Unparseable content yields an empty set.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()
    tops: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tops.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import: not an external top-level module
            if node.module:
                tops.add(node.module.split(".")[0])
    return tops


def check_imports(
    content: str,
    *,
    path: str = "",
    known_modules: set[str] | None = None,
) -> ImportReport:
    """Statically check ``content`` for unresolved top-level imports.

    Pure and in-memory: parses ``content`` with :mod:`ast` (no import is executed,
    no file is read). A top-level module is *missing* when it is neither part of
    the standard library (``sys.stdlib_module_names``) nor in ``known_modules``.

    Args:
        content: The artifact's text.
        path: The artifact's relative path (echoed for reporting; optional).
        known_modules: Top-level module names to treat as resolvable. Defaults to
            the revolver package's top-level name(s) (``_DEFAULT_KNOWN_MODULES``).

    Returns:
        An :class:`ImportReport` with the sorted list of missing top-level names.
    """
    known = set(_DEFAULT_KNOWN_MODULES) if known_modules is None else set(known_modules)
    missing = sorted(
        top
        for top in _top_level_imports(content)
        if top not in sys.stdlib_module_names and top not in known
    )
    return ImportReport(path=path, ok=not missing, missing=missing)


def validate_manifest_artifacts(
    manifest: ProposalManifest,
    *,
    known_modules: set[str] | None = None,
) -> list[ValidationResult]:
    """Validate the content of every NEW file in a manifest's proposal.

    Pure, dry-run, stdlib-only: operates on the in-memory ``content`` strings of
    each ``NewFile`` in ``manifest.proposal.new_files`` (no I/O, no process
    launch). For each file it runs :func:`check_syntax` and :func:`check_imports`
    and combines the outcomes into one :class:`ValidationResult`.

    Args:
        manifest: The ProposalManifest whose NEW files to validate.
        known_modules: Forwarded to :func:`check_imports` (defaults to the
            revolver package's top-level name(s)).

    Returns:
        One :class:`ValidationResult` per ``NewFile``, in stored (builder) order.
    """
    results: list[ValidationResult] = []
    for nf in manifest.proposal.new_files:
        syntax = check_syntax(nf.content, path=nf.path)
        imports = check_imports(nf.content, path=nf.path, known_modules=known_modules)
        errors: list[str] = []
        if not syntax.ok:
            errors.append(f"syntax: {syntax.error}")
        if not imports.ok:
            for name in imports.missing:
                errors.append(f"import: missing module {name!r}")
        results.append(
            ValidationResult(
                path=nf.path,
                syntax_ok=syntax.ok,
                imports_ok=imports.ok,
                errors=errors,
            )
        )
    return results
