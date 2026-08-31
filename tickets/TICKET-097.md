# TICKET-097: Dead constant `_OUTER_FRESHNESS_DRIVER_PATH` in `revolver/fixes.py`

Status: DONE
Cycle: 37 (synthesis audit)

## Purpose
`_OUTER_FRESHNESS_DRIVER_PATH` is a module-level constant that is defined but never
referenced. It is a leftover from the pre-derive outer-freshness generator and should
be removed alongside the dead embedded body (TICKET-095) so the outer-freshness
section carries only live symbols.

## Evidence
- `revolver/fixes.py:457` —
  `_OUTER_FRESHNESS_DRIVER_PATH = PROPOSAL_NAMESPACE + "outer_freshness_driver.sh"`.
- `grep -rn _OUTER_FRESHNESS_DRIVER_PATH revolver/ tests/ docs/` returns ONLY the
  definition at :457. No read site anywhere.
- Contrast with its sibling `_OUTER_FRESHNESS_RUNNER_PATH` (:455), which IS live:
  it is read at `revolver/fixes.py:650`
  (`replacement="RUN=" + _OUTER_FRESHNESS_RUNNER_PATH`).
- The driver's output path is produced by `derive()` from the instruction's
  `new_name="outer_freshness_driver.sh"` (revolver/fixes.py:651), so the constant is
  redundant even for the path it names.

## Impact
- Dead code; `ruff` does not flag module-level constants (no F841 for assignments),
  so it survives lint and silently misleads readers into thinking the driver path is
  assembled from a constant when it is actually the `new_name` of the instruction.
- Inconsistent with the derive-by-reference invariant: the path should come from the
  `ChangeInstruction`, not a parallel constant.

## Suggestion
Delete `revolver/fixes.py:457` (and its comment line :456). Keep
`_OUTER_FRESHNESS_RUNNER_PATH` (:455) — it is read at :650. Re-run
`ruff check revolver/` and `pytest tests/test_replay.py -q` (outer-freshness replay
tests are unaffected).

## Resolution (Cycle 38)
Deleted the dead constant `_OUTER_FRESHNESS_DRIVER_PATH` and its comment line from
`revolver/fixes.py`. Kept `_OUTER_FRESHNESS_RUNNER_PATH` (read at the `RUN=` replacement
site). No behavior change. Verified: `grep -rn --include='*.py' _OUTER_FRESHNESS_DRIVER_PATH
revolver/ tests/ docs/` returns nothing.
