# TICKET-041: plan_relaunch() + RelaunchPlan — resume-aware relaunch plan

Status: OPEN
Date: 2026-08-27
Cycle: 9 synthesis audit
Target: `revolver/relaunch.py` (NEW module) — resume-aware relaunch plan.

## Title
Add `RelaunchPlan` dataclass (first_cycle, last_cycle, resume_from, command, note)
and `plan_relaunch(manifest, *, cycles, done=None) -> RelaunchPlan`: build the
resume-aware relaunch plan.

## Evidence
- JUNIOR.md §8: "Continuation launches (FIRST > 1 with existing history): append,
  don't truncate — `nohup ./run-cycles.sh 13 14 >> cycles.out 2>&1 &`." The command
  must be scoped to `resume_from..last_cycle` and append (`>>`) to cycles.out.
- JUNIOR.md §7 scar (B1): a wall-clock kill must not force a full restart; resume
  from the first not-done cycle (R1 resume-union).
- `revolver/launch_plan.py::LaunchPlan` already carries `command` (the nohup line)
  and `cycles_out_append` (the marker). `plan_relaunch` reuses that command shape;
  it does NOT re-derive budgets.
- `first_not_done_cycle` (TICKET-040) supplies `resume_from`.

## Suggestion
`plan_relaunch(manifest, *, cycles, done=None) -> RelaunchPlan`:
- `first_cycle = min(cycles)`, `last_cycle = max(cycles)` (empty cycles -> 0/0).
- `resume_from = first_not_done_cycle(cycles, done=done)`.
- If `resume_from is None` (all done): no-op plan — empty command, note "all done".
- Else: command scoped to `resume_from..last_cycle`, reusing
  `manifest.launch_plan.command`'s shape (nohup + `>> cycles.out 2>&1 &`), note
  describing the resume range.
- Pure, deterministic, stdlib-only; no I/O, no process.
