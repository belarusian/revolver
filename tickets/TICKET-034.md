# TICKET-034: No-op plan must report ok with an explicit no-op note

## Title
A no-op `LaunchPlan` must be reported `ok=True` with a no-op note; no-op
detection and reporting are currently implicit and unreported.

## Evidence
- `revolver/launch_plan.py:163-177` builds the no-op plan with `command=""`,
  `cycles_out_append=""`, `request_timeout=0`, `outer_wall=0`, and
  `rationale="no-op (healthy); nothing to launch"`. There is no `no_op` field on
  `LaunchPlan` (launch_plan.py:56-66); the only signal is the empty command.
- `LaunchPlan.validate()` (launch_plan.py:97-131) passes a no-op plan (empty
  command is allowed, budgets are 0) but emits no *report* — it returns `self`
  or raises.
- `revolver/validation.py` has no `LaunchPlanReport` and no no-op branch, so a
  no-op plan cannot be reported as "ok with a no-op note".

## Impact
Without an explicit no-op report, a consumer of `check_launch_plan` cannot
distinguish "healthy, correctly nothing to launch" from "malformed empty
command". The cycle-7 contract requires a no-op plan to be reported `ok` with a
no-op note so the dry-run output is unambiguous.

## Suggestion
In `check_launch_plan`:
- detect no-op as `plan.command == ""` (and `plan.cycles_out_append == ""`);
- for a no-op plan, skip checks (a)-(e) and return
  `LaunchPlanReport(ok=True, no_op=True, errors=[], ...)` carrying a no-op note
  (e.g. `note="no-op (healthy); nothing to launch"`).
- for a non-no-op plan, run checks (a) nohup [TICKET-031], (b) append marker
  [TICKET-032], (c) endpoint verbatim [TICKET-033], (d) `request_timeout >=
  outer_wall`, (e) `one_pipeline_per_endpoint is True`.
Note: (d) and (e) are already enforced by `LaunchPlan.validate()`
(launch_plan.py:111, 124); `check_launch_plan` should re-check them in the
report so the report is self-contained, without relying on `validate()` raising.
