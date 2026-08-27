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
It also validates the derived dry-run :class:`~revolver.launch_plan.LaunchPlan`
as a *command* (nohup, append-not-truncate marker, verbatim endpoint pin,
request_timeout >= outer_wall, one pipeline per endpoint) — see
:func:`check_launch_plan` and :func:`validate_manifest_launch`.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from revolver.launch_plan import LaunchPlan

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


# ---------------------------------------------------------------------------
# Launch-plan validation (command-shape invariants)
# ---------------------------------------------------------------------------


@dataclass
class LaunchPlanReport:
    """Result of validating a :class:`LaunchPlan` as a *command*.

    Attributes:
        ok: True when the plan is launch-safe as a command (or is a no-op).
        errors: Human-readable failure strings (empty when ok). On a no-op plan
            this holds a single NOTE (``"no-op plan"``), not a failure — callers
            must branch on ``ok``, not on ``len(errors) == 0`` alone.
    """

    ok: bool
    errors: list[str] = field(default_factory=list)


def _has_truncate_redirect(text: str) -> bool:
    """True when ``text`` contains a truncate/overwrite redirect.

    A truncate redirect is a lone ``>`` that is not part of an append (``>>``).
    ``2>&1`` is not a redirect to a file and is ignored.
    """
    for i, ch in enumerate(text):
        if ch == ">" and (i + 1 >= len(text) or text[i + 1] != ">"):
            return True
    return False


def _is_noop(plan: LaunchPlan) -> bool:
    """True for a no-op plan: empty command, empty marker, zero budgets."""
    return (
        plan.command == ""
        and plan.cycles_out_append == ""
        and plan.request_timeout == 0
        and plan.outer_wall == 0
    )


def check_launch_plan(
    plan: LaunchPlan,
    *,
    endpoint_pin: str | None = None,
) -> LaunchPlanReport:
    """Validate a :class:`LaunchPlan` as a *command* (dry-run, no I/O).

    This checks the *command-shape* invariants that the structural
    :meth:`LaunchPlan.validate` does not cover. It does NOT re-derive the budgets
    or the command — it validates the plan ``build_launch_plan()`` already
    produced. Pure, deterministic, stdlib-only; no disk write, no process launch.

    Args:
        plan: The LaunchPlan to validate.
        endpoint_pin: An externally expected endpoint pin. When supplied, the
            plan's ``endpoint_pin`` must equal it verbatim. When ``None``, the
            check is a self-consistency check (the plan's own pin) and always
            passes.

    Returns:
        A :class:`LaunchPlanReport`. A no-op plan (empty command + marker, zero
        budgets) is reported ``ok`` with a single no-op note and no other checks
        run.
    """
    if _is_noop(plan):
        return LaunchPlanReport(ok=True, errors=["no-op plan"])

    errors: list[str] = []

    # (a) a non-no-op command must background the launch with nohup.
    if "nohup" not in plan.command.split():
        errors.append(
            "command must use nohup (background, survives the launching shell)"
        )

    # (b) the marker must be a non-empty append marker, never a truncate form.
    marker = plan.cycles_out_append
    if not marker:
        errors.append("cycles_out_append must be a non-empty append marker")
    elif not marker.endswith("\n"):
        errors.append("cycles_out_append must end with a newline")
    elif _has_truncate_redirect(marker):
        errors.append(
            "cycles_out_append must append (>>), never truncate/overwrite (>)"
        )

    # (c) the endpoint pin must match the expected pin verbatim (self-consistency
    #     when no expected pin is supplied).
    if endpoint_pin is not None and plan.endpoint_pin != endpoint_pin:
        errors.append(
            f"endpoint_pin {plan.endpoint_pin!r} != expected {endpoint_pin!r}"
        )

    # (d) the per-request budget must never undercut the outer wall.
    if plan.request_timeout < plan.outer_wall:
        errors.append(
            f"request_timeout ({plan.request_timeout}) must be >= outer_wall "
            f"({plan.outer_wall})"
        )

    # (e) one pipeline per endpoint.
    if not plan.one_pipeline_per_endpoint:
        errors.append("one_pipeline_per_endpoint must be True")

    return LaunchPlanReport(ok=not errors, errors=errors)


def validate_manifest_launch(
    manifest: ProposalManifest,
    *,
    endpoint_pin: str | None = None,
) -> LaunchPlanReport:
    """Validate the launch plan carried by a manifest (dry-run, no I/O).

    Runs :func:`check_launch_plan` over ``manifest.launch_plan`` and returns the
    single report. Pure, deterministic, stdlib-only; no disk write, no process
    launch.

    Args:
        manifest: The ProposalManifest whose launch plan to validate.
        endpoint_pin: Forwarded to :func:`check_launch_plan`.

    Returns:
        A :class:`LaunchPlanReport` for the manifest's launch plan.
    """
    return check_launch_plan(manifest.launch_plan, endpoint_pin=endpoint_pin)
