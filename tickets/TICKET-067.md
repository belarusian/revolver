# TICKET-067: replay acceptance tests for both founding fix classes

**Found:** 2026-08-27, operator re-prime (Build Order row "Fix-class templates + replay acceptance | 14-15").
**Status:** DONE — replay acceptance tests landed in tests/test_replay.py (12 tests, pure).
**Severity:** high — these tests are the project's acceptance contract.

## Evidence

Revolver-task.md done criteria:
- Replay test 1: cycle-8 diagnosis in -> generated path approx the hand-built v3 set (report the semantic diff)
- Replay test 2: cycle-11 diagnosis in -> driver variant with corrected inner wall, everything else byte-identical

No replay tests exist in `tests/` (the 327 passing CI tests cover the built machinery —
diagnosis / proposal / manifest / launch-plan / validation / deploy / relaunch / observe —
but none of the two founding use cases). The generators they would exercise are TICKET-065
and TICKET-066.

## Impact

CI is green while the project's acceptance contract is unverified. A future regression in
either fix-class generator would be invisible to the gate.

## Suggestion

- `tests/test_replay.py` (or extend `tests/test_fixes.py`): two acceptance tests, each a
  pure function of fixed inputs (deterministic — no clock, no filesystem beyond tmp_path,
  no network):
  1. **cycle-8 replay:** construct the cycle-8 Diagnosis (cancel-loop evidence), run the
     client-timeout builder, assert the generated set is semantically equivalent to the
     golden v3 shape: a timeout module whose context_aware_invoke passes an explicit
     request timeout from env FIVE_REQUEST_TIMEOUT; a runner + spoke variant each carrying
     the one-line import delta; a driver exporting FIVE_REQUEST_TIMEOUT >= its outer wall.
     Golden reference files are read-only inputs to the test (path constants), never
     copied into the repo.
  2. **cycle-11 replay:** construct the cycle-11 Diagnosis (wall-kill-after-merge on a
     heavy cycle), run the inner-wall builder with a fixed predecessor driver text, assert
     the generated driver's `--inner-seconds` increased and every other line is
     byte-identical to the input.
- Both tests must pass in CI (they are pure; no sentry import required — the diagnosis is
  constructed directly, which also keeps the optional-dependency pattern intact).
