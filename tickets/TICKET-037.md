# TICKET-037: LaunchReport + relaunch (execute the launch command; no process kill)

Status: DONE
Date: 2026-08-27
Cycle: 8 synthesis audit
Target: relaunch the pipeline driver on the deployed path (revolver/deploy.py).

## Evidence
- `revolver/launch_plan.py::LaunchPlan.command` is the launch-safe command
  (`nohup ... >> cycles.out 2>&1 &`) already produced by `build_launch_plan` and
  validated by `revolver/validation.py::check_launch_plan` (Cycle 7). `relaunch` must
  execute `manifest.launch_plan.command` — it does NOT re-derive it.
- JUNIOR.md §8: "kill the INNER pid only; never kill the driver." Process kill stays
  sentry's job. `relaunch` must contain NO kill/terminate logic — it only launches.

## Suggestion
Add to `revolver/deploy.py` a `LaunchReport` dataclass (ok, command, errors, note) and
`relaunch(manifest, *, launch=None, run_command=None) -> LaunchReport`: execute the
launch plan's command via an overridable `run_command` seam (default: a real subprocess
launch). A no-op plan (empty command) is reported ok with a "no-op" note and launches
nothing. No process kill — this only launches.

DONE — verified implemented in deploy.py (tests in test_deploy.py); closed out in Cycle 35.
