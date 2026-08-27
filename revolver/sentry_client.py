"""revolver.sentry_client — invoke ``sentry check`` via the pinned dependency.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: ``sentry/cli.py::main`` dispatches ``check`` to
``SentryCLI(project_dir).run_check()``, which ``print``s the stable 8-line dialect
(``_format_check_report``) and returns the house exit code (``EXIT_OK=0`` /
``EXIT_ACTION=1`` / ``EXIT_USAGE=2``). ``revolver/diagnosis.py::parse_sentry_report``
already parses that exact dialect into a ``Diagnosis`` (``source="sentry-report"``).
This module wraps the runner behind an overridable seam (the sentry pattern: an
injectable runner so tests never shell out) and maps the house exit code onto the
record. When the pinned ``sentry`` package is not importable it raises
``ImportError`` so the caller can degrade to raw-artifact parsing.

Deterministic, stdlib-only, pure functions with overridable I/O seams. Nothing here
writes to disk or kills a process.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import TYPE_CHECKING

from revolver.diagnosis import Diagnosis, parse_sentry_report

if TYPE_CHECKING:
    from collections.abc import Callable

# House exit-code convention (sentry): 0=healthy, 1=action needed, 2=usage error.
EXIT_OK = 0
EXIT_ACTION = 1
EXIT_USAGE = 2


class SentryClient:
    """Run ``sentry check`` through an overridable runner seam.

    The seam is :meth:`run_check`, which returns ``(stdout, exit_code)``. The
    default implementation imports the pinned ``sentry`` package and calls
    ``sentry.cli.main(["check", str(project_dir)])`` capturing stdout via
    ``contextlib.redirect_stdout`` and returning the int it yields. Tests override
    :meth:`run_check` on an instance so nothing ever shells out.
    """

    def run_check(self, project_dir: str | Path) -> tuple[str, int]:
        """Run ``sentry check <project_dir>`` and return ``(stdout, exit_code)``.

        Raises:
            ImportError: if the pinned ``sentry`` package is not importable.
        """
        try:
            import sentry.cli
        except ImportError as exc:  # pragma: no cover - exercised via seam in tests
            raise ImportError("sentry package is not importable") from exc

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = sentry.cli.main(["check", str(project_dir)])
        return buf.getvalue(), int(result)


def diagnose_via_sentry(
    project_dir: str | Path,
    *,
    client: SentryClient | None = None,
    read_file: Callable[[Path], str] | None = None,
) -> Diagnosis:
    """Diagnose a project directory via the sentry check runner.

    Calls the runner seam, parses its stdout with
    :func:`revolver.diagnosis.parse_sentry_report` (``source="sentry-report"``), and
    maps the house exit code onto the record:

    * exit code 2 -> a usage error is surfaced in ``evidence`` and ``exit_code``
      reports 2;
    * exit code 0/1 -> ``action_needed`` is derived from the parsed report and
      ``exit_code`` reports the house code.

    Args:
        project_dir: Path to the project directory.
        client: Optional :class:`SentryClient` (defaults to a fresh client).
        read_file: Overridable I/O seam (kept for symmetry with ``diagnose``; the
            sentry path does not read raw artifacts).

    Returns:
        A ``Diagnosis`` with ``source="sentry-report"``.

    Raises:
        ImportError: if the runner seam cannot import the pinned sentry package.
    """
    if client is None:
        client = SentryClient()

    stdout, exit_code = client.run_check(project_dir)
    d = parse_sentry_report(stdout)
    d.sentry_exit_code = exit_code

    if exit_code == EXIT_USAGE:
        d.evidence = (d.evidence + "; " if d.evidence else "") + (
            f"sentry usage error (exit code {exit_code})"
        )
    return d
