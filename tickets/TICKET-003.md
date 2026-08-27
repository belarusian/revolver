# TICKET-003: revolver.diagnosis — round-trip + validation + exit-code convention

**Title:** Give `Diagnosis` a lossless round-trip (`to_dict`/`from_dict`), validation, and the house exit-code convention.

**Evidence:** House convention (sentry/cli.py): 0 = healthy, 1 = action needed,
2 = usage error. The briefing requires a "typed, versioned Diagnosis record" with
"round-trip + validation tests."

**Impact:** Without `to_dict`/`from_dict` and an `action_needed`/`exit_code` property,
the record cannot be serialized for the proposal stage (cycles 3-5) or asserted in tests.

**Suggestion:** Add `to_dict()`, `from_dict()`, `action_needed` and `exit_code`
properties, and a `validate()` that raises on unknown `source`/`verdict`/`stall_action`.
