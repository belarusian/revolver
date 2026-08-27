# TICKET-038: overridable seams keep deploy/relaunch pure + testable

Status: OPEN
Date: 2026-08-27
Cycle: 8 synthesis audit
Target: seam design (revolver/deploy.py).

## Evidence
- The package contract (revolver/__init__.py) is "deterministic, stdlib-only". Cycles
  1-7 established the seam pattern: `sentry_client.py::SentryClient.run_check`,
  `diagnosis.py::diagnose(read_file=...)`, `manifest.py::build_manifest(builders=...)`.
  Tests use `patch.object(instance, "method")` (Rule 4) and injectable seams so nothing
  touches the real filesystem or spawns a real process.
- The real disk write and the real process launch are the only I/O in this module; both
  must be injectable so the module's *logic* (which paths to write, whether to launch,
  the report shape) stays pure and deterministic.

## Suggestion
`deploy_manifest` takes `write_file` (default: real `open(..., "w")`) and `approved`
(default: a human-approval callable returning False) as overridable seams. `relaunch`
takes `run_command` (default: a real subprocess launch) as an overridable seam. Tests
inject fakes so nothing touches the real filesystem or spawns a real driver. The
default implementations do the real I/O; the logic is pure.
