# TICKET-079 — Split of TICKET-077 (cycle 18, re-scoped): migrate build_inner_wall_fix to derive

**Status: DONE**
**Source: composer split of cycle 18 (TICKET-077) — one builder per bounded pass.**

## Scope (this pass ONLY)
Rewrite `build_inner_wall_fix(diagnosis, *, predecessor_driver)` in `revolver/fixes.py`
as a THIN INSTRUCTION EMITTER over `revolver.derive`:
- Single `ChangeInstruction`: predecessor = the resolved driver PATH (no embedded text),
  one stated edit replacing the `--inner-seconds` value; everything else byte-identical.
- Call `derive(predecessor, instruction)`; return the resulting `list[NewFile]`.
- Keep the public signature additive-compatible.

## Hard requirements
- No embedded driver body in this builder after the change.
- Additive only; stdlib only; deterministic.
- Gate: `pytest tests/ -x -q` (monotonic, no regressions) + `ruff check revolver/` +
  `mypy revolver/ --ignore-missing-imports`.
- PR merged on main; log block appended.

## Out of scope (later passes)
- `build_client_timeout_fix` (TICKET-080) and `build_outer_freshness_fix` (TICKET-081).
- Do NOT touch the grep replay tests (that is TICKET-078, a separate row).

## Resolution
Merged cycle 19, PR #94 (commit c7bf0ec).
