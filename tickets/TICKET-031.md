# TICKET-031: validate_manifest_launch() — run check_launch_plan over manifest.launch_plan

## Title
Add `validate_manifest_launch(manifest, *, endpoint_pin=None) -> LaunchPlanReport` to
`revolver/validation.py`: run `check_launch_plan` over `manifest.launch_plan` and return
the single report.

## Evidence
- `revolver/manifest.py` `ProposalManifest` carries a `launch_plan: LaunchPlan`.
- The briefing requires `validate_manifest_launch` over every failure_mode to yield an ok
  report, and a manifest with a broken launch plan to yield a failing report.

## Suggestion
Pure, dry-run, stdlib-only, no I/O, no process launch. Thin wrapper:
`return check_launch_plan(manifest.launch_plan, endpoint_pin=endpoint_pin)`. No re-derivation.
