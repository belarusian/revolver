# TICKET-069 — generator unit tests (build_client_timeout_fix + build_inner_wall_fix)

**Status:** DONE
**Cycle:** 14 (Fix-class templates + replay acceptance, cycles 14-15)

## Capability
Unit tests for the two new generators in `revolver/fixes.py` (distinct from the replay
acceptance tests in TICKET-067, which assert semantic equivalence to the golden
reference). These cover the structural contract:
- `build_client_timeout_fix`: emits exactly the four NEW files (chat-model module,
  runner variant, spoke variant, driver variant); every path under
  `PROPOSAL_NAMESPACE`; every content embeds "Diff from predecessor:" + "Evidence:";
  the chat-model module passes the timeout to BOTH impls; the runner and spoke carry the
  one-line import delta; the driver exports `FIVE_REQUEST_TIMEOUT` >= its outer wall and
  repoints RUN/SPOKE; pure + deterministic (same input -> same output).
- `build_inner_wall_fix`: emits exactly ONE NEW file; the only delta vs the predecessor
  driver text is the `--inner-seconds` value (everything else byte-identical); the new
  value is derived from the observed heaviest inner duration when present, else a stated
  margin over the old value; pure + deterministic.
- Both builders are registered in `FIX_BUILDERS` and reachable via `propose()`.

## Invariants
- Pure, deterministic, stdlib-only; no disk write, no clock, no randomness.
- Additive only (hard rule 7): no existing-path collision.
