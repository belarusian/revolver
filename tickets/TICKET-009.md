# TICKET-009: tests/test_sentry_client.py — runner-seam tests

Status: DONE
**Title:** Add `tests/test_sentry_client.py` covering the runner seam: check stdout ->
`Diagnosis` round-trip; not-importable -> raw-artifacts fallback; exit-code passthrough.

**Evidence:**
- `tests/test_diagnosis.py` and `tests/test_sentry_pin.py` exist; no `test_sentry_client.py`.
- `SentryClient.run_check` (TICKET-006) is the overridable seam; tests must inject it so
  nothing shells out.
- House exit-code convention: 0=healthy, 1=action needed, 2=usage error.

**Impact:** The new client is untested; the degradation path and exit-code mapping are
unverified.

**Suggestion:**
- Test: inject a fake `run_check` returning a canned 8-line report + exit 1 ->
  `diagnose_via_sentry` yields `source="sentry-report"`, correct fields, `action_needed=True`,
  `exit_code=1`.
- Test: exit 0 -> `action_needed=False`, `exit_code=0`.
- Test: exit 2 -> usage error surfaced (evidence / exit_code=2).
- Test: `sentry` not importable (seam raises ImportError) -> `diagnose()` falls back to
  `source="raw-artifacts"` and says so.
- Use `patch.object(instance, "run_check")` (Rule 4), not constructor-level patches.

DONE — verified implemented in sentry_client.py (tests in test_sentry_client.py); closed out in Cycle 36.
