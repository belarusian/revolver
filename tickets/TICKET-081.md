# TICKET-081 — Split of TICKET-077 (cycle 18, re-scoped): migrate build_outer_freshness_fix to derive

**Status: Open**
**Source: composer split of cycle 18 (TICKET-077) — one builder per bounded pass.**

## Scope (this pass ONLY)
Rewrite `build_outer_freshness_fix(diagnosis, *, predecessor_runner)` in
`revolver/fixes.py` as a THIN INSTRUCTION EMITTER over `revolver.derive`:
- Derive `run-v4` from triple `run-v3.py` with the one stated edit (task-template
  replacement adding the pass-freshness guard — emit the replacement text as the
  instruction's `replacement` data, citing trajectory_0027/0029).
- Plus a driver repoint instruction (`RUN=…/run-v4.py`).
- This MIGRATES the PR #89 value-embedding builder onto the new architecture.

## Hard requirements
- No embedded runner body in this builder after the change.
- Additive only; stdlib only; deterministic.
- Gate: `pytest tests/ -x -q` (monotonic) + `ruff check revolver/` +
  `mypy revolver/ --ignore-missing-imports`.
- PR merged on main; log block appended.

## Out of scope
- Do NOT touch the grep replay tests (TICKET-078).
