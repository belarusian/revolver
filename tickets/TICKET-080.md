# TICKET-080 — Split of TICKET-077 (cycle 18, re-scoped): migrate build_client_timeout_fix to derive

**Status: DONE**
**Source: composer split of cycle 18 (TICKET-077) — one builder per bounded pass.**

## Scope (this pass ONLY)
Rewrite `build_client_timeout_fix(diagnosis)` in `revolver/fixes.py` as a THIN
INSTRUCTION EMITTER over `revolver.derive` — FOUR `ChangeInstruction`s, each
predecessor a resolved PATH (no embedded text):
1. chat-model predecessor (pinned meta reference, sha256 discipline) + one stated edit
   inserting `timeout=FIVE_REQUEST_TIMEOUT`.
2. triple `run-v3.py` + one import-swap to the derived chat-model module.
3. triple `cycle-implementation-v4.py` + one import-swap.
4. triple `run-cycles-v3.sh` + one export edit (`FIVE_REQUEST_TIMEOUT=21600` and/or
   RUN+SPOKE repointed to the staged paths).
- Version names follow hard-rule-7 (next free `vN`), chosen by the builder, never
  hard-coded in the ticket.
- The staged set cross-references by PATH.

## Hard requirements
- No embedded chat-model/runner/spoke/driver body in this builder after the change.
- Additive only; stdlib only; deterministic.
- Gate: `pytest tests/ -x -q` (monotonic) + `ruff check revolver/` +
  `mypy revolver/ --ignore-missing-imports`.
- PR merged on main; log block appended.

## Out of scope
- `build_outer_freshness_fix` (TICKET-081). Do NOT touch the grep replay tests.
