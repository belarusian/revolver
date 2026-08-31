# TICKET-015: LaunchPlan dataclass + build_launch_plan(proposal)

Status: DONE
Cycle: 4 (additive proposal)

## What's missing
No `LaunchPlan` type and no pure dry-run derivation from a `RepairProposal`.
A repair launch today would be hand-written bash; the house invariants
(nohup, append to cycles.out, endpoint pin verbatim, FIVE_REQUEST_TIMEOUT >=
outer wall, one pipeline per endpoint) live only in prose.

## Target
`revolver/launch_plan.py`:
- `LaunchPlan` dataclass: pipeline_id, command, cycles_out_append, endpoint_pin,
  request_timeout, outer_wall, one_pipeline_per_endpoint, rationale, version.
- `build_launch_plan(proposal) -> LaunchPlan`: pure, deterministic. Healthy
  (empty) proposal -> no-op plan.
- `validate()` raising if any invariant is violated.
- lossless `to_dict`/`from_dict`.

## Evidence
Seed: chat_model_v2.py:53 (FIVE_REQUEST_TIMEOUT default 21600 > max outer wall
10800); JUNIOR.md §3 (one pipeline per endpoint), §8 (append not truncate).

DONE — verified implemented in launch_plan.py (tests in test_launch_plan.py); closed out in Cycle 35.
