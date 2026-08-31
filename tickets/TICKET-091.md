# TICKET-091: Close-out verification — launch_plan.py (TICKET-015..019)

Status: DONE
Cycle: 35 (synthesis audit)
Parent: TICKET-015, TICKET-016, TICKET-017, TICKET-018, TICKET-019

## Purpose
Close-out verification for the stale backlog tickets TICKET-015..019. Confirms
each ticket's named symbol exists in `revolver/launch_plan.py` (and the
multi-file marker path in `revolver/fixes.py`) and that the module's test
module passes, so the tickets can be flipped OPEN -> DONE.

## Evidence (symbol presence)
- TICKET-015 `LaunchPlan` dataclass: `revolver/launch_plan.py:40`
  (fields pipeline_id, command, cycles_out_append, endpoint_pin, request_timeout,
  outer_wall, one_pipeline_per_endpoint, rationale, version).
- TICKET-015 `build_launch_plan(proposal)`: `revolver/launch_plan.py:146`.
- TICKET-016 multi-file repair path (plan + cycles.out marker): each actionable
  builder in `revolver/fixes.py` returns TWO `NewFile`s — plan file
  (`_PLAN_PATHS`, line 29) + marker file (`_MARKER_PATHS`, line 34). Verified for
  driver-death (lines 104/110), wall-kill (147/153), stall-kill (191/197);
  `build_none_fix` (line 205) stays empty.
- TICKET-017 `LaunchPlan.validate()`: `revolver/launch_plan.py:97` (raises on
  request_timeout < outer_wall, empty command, one_pipeline_per_endpoint False).
- TICKET-018 `tests/test_launch_plan.py`: present, 31 tests.
- TICKET-019 purity/determinism: `build_launch_plan` builds the command string
  (nohup + `>> cycles.out 2>&1 &`, lines 189-193) — no subprocess, no disk write,
  no clock.

## Test evidence
`pytest tests/test_launch_plan.py -q` -> 31 passed.

## Verdict
All five tickets' named symbols exist and the test module is green. Flip
TICKET-015..019 OPEN -> DONE.
