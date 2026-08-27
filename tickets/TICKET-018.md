# TICKET-018: tests/test_launch_plan.py round-trip + invariants

Status: OPEN
Cycle: 4 (additive proposal)

## What's missing
No tests for the launch plan.

## Target
`tests/test_launch_plan.py`: each failure_mode yields a valid LaunchPlan; endpoint
pin verbatim; request_timeout >= outer_wall; one pipeline per endpoint; healthy ->
no-op; to_dict/from_dict lossless; validate() raises on a broken plan.

## Evidence
House test convention (test_proposal.py round-trip style).
