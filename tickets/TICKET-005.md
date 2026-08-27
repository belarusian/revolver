# TICKET-005: tests — round-trip + validation for Diagnosis and sentry pin

**Title:** Add `tests/test_diagnosis.py` (and pin coverage) with round-trip + validation tests.

**Evidence:** The briefing lists `tests/test_diagnosis.py` as a target: "Round-trip +
validation tests for the Diagnosis record and sentry pin resolution." A partial
`tests/test_diagnosis.py` exists on branch `cycle-1-diagnosis` but no pin tests exist.

**Impact:** No merged tests on main for either module; the gate would not exercise the
new code.

**Suggestion:** Add `tests/test_diagnosis.py` covering `parse_sentry_report`,
`parse_raw_artifacts`, `diagnose` (I/O seam), `to_dict`/`from_dict` round-trip,
`validate()`, and `exit_code`; plus `tests/test_sentry_pin.py` covering
`parse_requirement`/`render_requirement` round-trip and `validate_pin` (rejects
branch/tag/short-sha).
