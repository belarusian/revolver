# TICKET-006: revolver.sentry_client — invoke `sentry check` via the pinned dependency

**Title:** Add `revolver/sentry_client.py` that runs `sentry check <project-dir>` through an
overridable runner seam (no live tree, no shell-out in tests) and parses its stdout into a
`Diagnosis` with `source="sentry-report"`.

**Evidence:**
- `sentry/cli.py::main` dispatches `check` to `SentryCLI(project_dir).run_check()`, which
  `print`s the stable 8-line dialect (`_format_check_report`) and returns the house exit
  code (`EXIT_OK=0` / `EXIT_ACTION=1` / `EXIT_USAGE=2`).
- `revolver/diagnosis.py::parse_sentry_report` already parses that exact 8-line dialect into
  a `Diagnosis` (source="sentry-report").
- `revolver/sentry_pin.py` pins sentry at sha `9713735c0b588e271f277a4b2b9f377ffbe2681c`.
- The current `diagnose()` has a TODO comment: "When sentry is importable we would invoke
  `sentry check` ... That wiring lives in the CLI layer (a later cycle)."

**Impact:** sentry is not yet consumed as the pinned git dependency it is supposed to be;
`diagnose()` can never produce a `source="sentry-report"` record.

**Suggestion:**
- New module `revolver/sentry_client.py` with a `SentryClient` exposing an overridable
  `run_check(project_dir) -> (stdout, exit_code)` seam (the sentry pattern: injectable
  runner so tests never shell out).
- `run_check` default: import the pinned `sentry` package and call
  `sentry.cli.main(["check", str(project_dir)])` capturing stdout (contextlib.redirect_stdout)
  and the returned int.
- `diagnose_via_sentry(project_dir) -> Diagnosis`: call the seam, `parse_sentry_report(stdout)`,
  and map the exit code onto the record (exit_code 2 -> usage error; 0/1 -> action_needed).
- Degrade to raw-artifacts when `sentry` is not importable (ImportError) — record provenance.
