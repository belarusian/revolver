# TICKET-054 — cross-cutting invariants (read-only, pure, seams)

**Cycle:** 11 (Observe + report)
**Module:** `revolver/observe.py`

## Invariants (verified by the full suite + gate)
- READ-ONLY: no process launch, no process kill, no write. The only I/O is through the
  overridable seams (`read_cycles_out`, `read_trajectory`); the default seams do the real
  file reads, but the logic is pure.
- Pure, deterministic, stdlib-only.
- Position is the only order: trajectory outcomes are reported in file order, never
  reordered or deduped.
- Honest gaps carry into the verdict: a cycle that is a gap (no marker) is evidence the
  run did not complete and can drive `recurred` True when a done marker was expected;
  the observer never assumes done (JUNIOR.md §7 scar).
- The recurrence verdict is a pure composition, not a re-diagnosis: `report` takes the
  diagnosed `failure_mode` as a *given* and asks whether the observed run shows it
  recurring; it does NOT re-run the diagnosis.
- Gate: `pytest tests/ -x -q` + `ruff check revolver/` + `mypy revolver/
  --ignore-missing-imports` all green.
