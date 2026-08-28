# TICKET-073 — deterministic replay acceptance tests (poisoning vs guard)

**Status:** Open
**Cycle:** 16
**Build Order row:** Outer-freshness guard — run-v4 meta-derivation (16)

## Capability
`tests/test_replay.py`: DETERMINISTIC replay acceptance tests, no endpoints, no
wall-clocks. Seed a stale trajectory `exit:task_complete` + an inner stub
`sleep 2; exit 124` (or direct content-level assertion of the generated run-v4 text):
- the run-v3-shaped reader must reproduce the poisoning (accepts the stale DONE as
  completion);
- the run-v4-shaped reader must re-invoke (never accept the stale file as completion).

Also: docstring-carry + additive-path validation (existing `validate()`) must pass on
every generated file. Test count is monotonic (only grows).

## Acceptance
- A v3-shaped reader over the seeded stale trajectory returns "accepts completion".
- A v4-shaped reader over the same seed returns "re-invoke" (dead-unwitnessed).
- Every generated file passes `RepairProposal.validate()` and `check_syntax`.
