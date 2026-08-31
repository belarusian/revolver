# TICKET-030: LaunchPlanReport dataclass + check_launch_plan() command-shape validator

Status: DONE

## Title
`revolver/validation.py` has no launch-plan validator. Add `LaunchPlanReport(ok, errors)`
and `check_launch_plan(plan, *, endpoint_pin=None) -> LaunchPlanReport` that validates a
`LaunchPlan` **as a command** (command-shape invariants the structural
`LaunchPlan.validate()` does not cover).

## Evidence
- `revolver/launch_plan.py` defines `LaunchPlan` (pipeline_id, command,
  cycles_out_append, endpoint_pin, request_timeout, outer_wall,
  one_pipeline_per_endpoint, rationale, version) and a structural `validate()`.
- `revolver/validation.py` (Cycle 6) validates NEW-file *content* (syntax/imports) but
  says nothing about the launch plan.
- JUNIOR.md §8: continuation launches must `nohup ... >> cycles.out 2>&1 &` (append,
  never truncate); §7 scar: a `>` on an existing filename wiped prior markers.

## Suggestion
`LaunchPlanReport` dataclass: `ok: bool`, `errors: list[str]` (empty when ok; on a no-op
this holds a NOTE, not a failure). `check_launch_plan` is pure, dry-run, stdlib-only, no
I/O, no process launch. It must NOT re-derive budgets/command — it validates the plan
`build_launch_plan()` already produced. Checks (each failure appends a descriptive
string; `ok` is True iff no failures):
1. no-op short-circuit: empty command + empty marker + zero budgets -> `ok=True` with a
   "no-op" note, no other checks run.
2. nohup: a non-no-op `command` must use `nohup` (word check).
3. append-not-truncate: `cycles_out_append` non-empty, ends with a newline, and is not a
   truncate/overwrite form (a lone `>` not part of `>>`).
4. endpoint_pin verbatim: `plan.endpoint_pin == endpoint_pin` when `endpoint_pin` is
   supplied; otherwise a self-consistency check (always passes).
5. request_timeout >= outer_wall (equality allowed; compare as ints).
6. one_pipeline_per_endpoint is True.

DONE — verified implemented in validation.py (tests in test_validation.py); closed out in Cycle 35.
