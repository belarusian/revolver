# TICKET-048: observe module invariants — read-only, no process launch/kill, position is the only order

Status: DONE
Date: 2026-08-27
Cycle: 10 synthesis audit
Target: `revolver/observe.py` (NEW module) — cross-cutting invariants.

## Title
Enforce the cross-cutting invariants across the observe module: READ-ONLY (no
process launch, no process kill, no write) and POSITION IS THE ONLY ORDER (markers
reported in file order, never reordered or deduped).

## Evidence
- JUNIOR.md §8: "kill the INNER pid only; the outer re-invokes (2-phase). Never
  kill the driver." Observation is read-only — it reads cycles.out and (later
  cycles) trajectories; it never launches or kills a process and never writes.
- JUNIOR.md §1: "append-only ground truth — position is the only order; never
  reorder, never rewrite". A cycle may appear more than once across restarts; the
  observer must not dedupe by cycle number.
- The seams (read_cycles_out, markers, done_pattern) keep the module pure +
  testable; the default read_cycles_out does the real file read but the logic is
  pure.

## Impact
If the observer wrote, launched, or killed anything it would violate the
read-only contract and could corrupt the very cycles.out it is observing. If it
reordered or deduped markers it would violate "position is the only order" and
lose the restart history the §7 union rule depends on.

## Suggestion
- No `subprocess` / `os.kill` / `signal` / write logic anywhere in observe.py.
- parse_cycle_markers returns markers in file order; never sort, never dedupe.
- observe() is read-only: the only I/O is through the seams (read_cycles_out).
- Pure, deterministic, stdlib-only.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 35.
