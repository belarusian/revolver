# TICKET-088 — No determinism test for build_client_timeout_fix / build_inner_wall_fix

**Status:** DONE
**Cycle:** 32 (synthesis audit)
**Parent:** TICKET-069

## Evidence

TICKET-069 (tickets/TICKET-069.md) states under "Invariants":
> Pure, deterministic, stdlib-only; no disk write, no clock, no randomness.

And under the capability for each builder:
> pure + deterministic (same input -> same output)

No test in `tests/test_replay.py` or any other test file asserts that calling
the builder twice with the same `Diagnosis` produces identical output.

The builders are documented as pure (fixes.py line 264: "Pure, deterministic,
stdlib-only. No disk writes, no clock, no randomness."), but the property is
unverified by the test suite. A regression that introduces non-determinism
(e.g., a `datetime.now()` call, a `random` seed, a dict-iteration-order
dependency) would not be caught.

## Impact

A silent non-determinism regression would produce different repair paths on
each invocation. In the closed loop, this means the deployed files could
differ from the approved proposal, violating the human-approval contract.
The observer's recurrence check would compare against a different baseline.

## Suggestion

Add to `tests/test_fixes.py`: