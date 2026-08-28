# TICKET-066: inner-wall fix-class generator (sentry cycle 11)

**Found:** 2026-08-27, operator re-prime (Build Order row "Fix-class templates + replay acceptance | 14-15").
**Status:** DONE — implemented in revolver/fixes.py (build_inner_wall_fix); replay acceptance in tests/test_replay.py.
**Severity:** high — the simple replay acceptance test ("if you can't do the simple one cleanly, stop").

## Evidence

Revolver-task.md founding use case 2: given "heavy cycle merged its PR then died on its
own inner wall (rc=124) before Phase 6/emit; outer completed the bookkeeping", revolver
must produce a driver variant with a larger `--inner-seconds` — everything else
byte-identical, docstring stating the diff and the cycle-11 evidence.

The incident (sentry cycle 11, 2026-08-27): a heavy cycle (new module + wiring + tests +
PR + CI polling) merged PR #47 at 04:49:00Z; the inner's own 3000s wall fired ~30s later
(rc=124 in the outer's trajectory) — after the merge, before Phase 6 (log block + next
briefing) and before its trajectory emit. The outer verified the merge on disk and
completed the bookkeeping itself (proven safe). The fix class: size `--inner-seconds` to
the heaviest expected cycle.

The current `revolver/fixes.py` has no builder for this class: the wall-kill builder emits
a generic remerge-plan file, not a driver variant with a corrected inner wall.

## Impact

Without this builder, revolver cannot propose the minimal fix for the second founding
failure class. The simple replay test is unrunnable.

## Suggestion

- New builder in `revolver/fixes.py` (or a new module if cleaner): given a Diagnosis of
  the inner-wall class (a wall-killed heavy cycle that DID merge — distinguishable from
  wall-kill-no-merge by the presence of the merge commit / gate block), emit ONE new file:
  a driver variant whose only delta is a larger `--inner-seconds` (derived from the
  observed heaviest inner duration when available, else a stated margin over the old
  value), with a docstring stating the diff + the cycle-11 evidence. Everything else in
  the generated driver is byte-identical to its predecessor by construction (the generator
  takes the predecessor driver text as input and applies the single substitution).
- Replay acceptance test: cycle-11 diagnosis in -> generated driver variant; assert the
  inner wall increased and every other line is byte-identical to the input driver.
