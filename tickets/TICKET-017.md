# TICKET-017: LaunchPlan invariants + validate()

Status: DONE
Cycle: 4 (additive proposal)

## What's missing
The house launch-plan invariants are unenforced: nohup, append to cycles.out,
endpoint pin verbatim, FIVE_REQUEST_TIMEOUT >= outer wall, one pipeline per
endpoint.

## Target
Encode as `LaunchPlan` fields + a `validate()` that raises ValueError if any is
violated (e.g. request_timeout < outer_wall, command not nohup, cycles_out_append
not set, one_pipeline_per_endpoint False, endpoint pin not verbatim from the
diagnosis).

## Evidence
Seed: chat_model_v2.py:17-18 (timeout > any external wall, max 10800s);
JUNIOR.md §3/§8.

DONE — verified implemented in launch_plan.py (tests in test_launch_plan.py); closed out in Cycle 35.
