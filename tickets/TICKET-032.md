# TICKET-032: build_launch_plan must emit a nohup + append command (so check_launch_plan passes)

## Title
`build_launch_plan()` (revolver/launch_plan.py) currently emits an actionable command
WITHOUT `nohup` and WITHOUT the `>> cycles.out` append redirect. Cycle 7's
`check_launch_plan` requires a non-no-op command to use `nohup`, and
`validate_manifest_launch` must yield an ok report for every failure_mode — so the
builder must emit a launch-safe command.

## Evidence
- Current actionable command: `revolver launch --pipeline ... --endpoint ... --failure-mode ...`
  (no nohup, no redirect).
- JUNIOR.md §8 canonical form: `nohup ./run-cycles.sh 13 14 >> cycles.out 2>&1 &`.
- The marker `cycles_out_append` already ends with a newline and is append-safe.

## Suggestion
Prefix the actionable command with `nohup` and append the `>> cycles.out 2>&1 &`
redirect, e.g. `nohup revolver launch --pipeline ... --endpoint ... --failure-mode ...
>> cycles.out 2>&1 &`. Keep it deterministic, stdlib-only, pure. The no-op (healthy)
plan stays empty command/marker with zero budgets.
