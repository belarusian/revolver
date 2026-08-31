# TICKET-016: Multi-file repair path (plan file + cycles.out marker)

Status: DONE
Cycle: 4 (additive proposal)

## What's missing
Each actionable failure mode emits a single plan file. The house convention is a
multi-file repair path: the plan file PLUS a `cycles.out` marker file (the
observer's input; append, never truncate).

## Target
Extend `revolver/fixes.py` builders (driver-death, wall-kill, stall-kill) to emit
two NewFiles each: the existing plan file + a NEW `revolver/fixes/<mode>_cycles.out`
marker file. Both carry the diff-from-predecessor + evidence docstring.
`none` stays empty. Additions-only (hard rule 7) preserved.

## Evidence
Seed: JUNIOR.md §8 (continuation launches append `>> cycles.out`; a `>` truncates
prior markers — the scar that lost markers 1-12).

DONE — verified implemented in fixes.py (tests in test_fixes_generators.py); closed out in Cycle 35.
