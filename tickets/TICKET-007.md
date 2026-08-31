# TICKET-007: revolver.diagnosis — try sentry first, fall back to raw-artifacts

Status: DONE
**Title:** Extend `diagnose()` to try sentry first (when importable), then fall back to
`parse_raw_artifacts`, recording the provenance in `source`.

**Evidence:**
- `revolver/diagnosis.py::diagnose(project_dir, *, read_file=None, sentry_available=None)`
  currently only ever returns `parse_raw_artifacts(...)`. The sentry branch is a comment.
- `parse_sentry_report` and `parse_raw_artifacts` both exist and are pure.
- `sentry_client.diagnose_via_sentry` (TICKET-006) will supply the sentry path.

**Impact:** Provenance is never "sentry-report" from the high-level entry point; the
degradation story is incomplete.

**Suggestion:**
- In `diagnose()`: when `sentry_available` is True (or resolves True), call
  `sentry_client.diagnose_via_sentry(project_dir, read_file=...)`; on success return it.
- On `ImportError` (sentry not installed) or a runner failure, fall back to
  `parse_raw_artifacts(...)` and ensure `source="raw-artifacts"` + an evidence note that
  sentry was unavailable.
- Keep the `sentry_available` override and the `read_file` seam for tests.

DONE — verified implemented in diagnosis.py (tests in test_sentry_client.py); closed out in Cycle 36.
