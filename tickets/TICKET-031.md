# TICKET-031: Non-no-op launch command must use nohup — neither generated nor validated

## Title
A non-no-op `LaunchPlan.command` must be `nohup`-prefixed; the generator omits it
and no validator checks for it.

## Evidence
- `revolver/launch_plan.py::build_launch_plan` builds the actionable command at
  line 181-184:
    `command = f"revolver launch --pipeline {proposal.pipeline_id} --endpoint
     {d.endpoint_pin} --failure-mode {d.failure_mode}"`
  — no `nohup`, no `&`, no redirect.
- `grep -rn "nohup" revolver/ tests/` returns nothing.
- Grounding (four repo): `JUNIOR.md` §8 — "Continuation launches (FIRST > 1 with
  existing history): append, don't truncate — `nohup ./run-cycles.sh 13 14 >>
  cycles.out 2>&1 &`"; §2 — "A command that nohup-launches a long job can hang
  the channel *after* the launch succeeded." `pipelines/v2/run-cycles.sh:7`
  documents `nohup ./run-cycles.sh 3 6 > cycles.out 2>&1 &`.

## Impact
A launch command that is not `nohup`-backgrounded will hold the invoking channel
open for the whole wall-clock budget (or hang it after launch), defeating the
dry-run→deploy handoff. Because no validator checks the command string, a
non-nohup command is indistinguishable from a valid one.

## Suggestion
- In `check_launch_plan`, when the plan is *not* a no-op (see TICKET-034),
  require `plan.command.lstrip().startswith("nohup ")`; otherwise record
  `nohup_ok=False` and an error string.
- Optionally, have `build_launch_plan` emit a `nohup`-prefixed command so the
  generated artifact and the validator agree.
