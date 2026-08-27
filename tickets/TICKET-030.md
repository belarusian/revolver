# TICKET-030: No launch-plan command-shape validation surface in revolver/validation.py

## Title
Cycle-7 target `check_launch_plan(plan, *, endpoint_pin=None) -> LaunchPlanReport`
and `validate_manifest_launch(manifest, *, endpoint_pin=None)` do not exist.

## Evidence
- `revolver/validation.py` defines only `SyntaxReport` (line 33), `ImportReport`
  (line 50), `ValidationResult` (line 66), `check_syntax` (line 87),
  `check_imports` (line 136), and `validate_manifest_artifacts` (line 166).
  `grep -rn "check_launch_plan\|validate_manifest_launch\|LaunchPlanReport"
  revolver/ tests/` returns nothing.
- The module docstring (lines 1-13) scopes the module to *NEW-file content*
  validation (syntax + imports) and says nothing about validating a `LaunchPlan`
  *as a command*.
- `revolver/manifest.py::ProposalManifest.validate()` (lines ~120-135) calls
  `proposal.validate()` and `launch_plan.validate()` but never inspects the
  launch plan's *command shape*.

## Impact
The cycle-7 synthesis deliverable (validate a `LaunchPlan` as a command) has no
entry point. A `LaunchPlan` whose command is malformed (no `nohup`, a truncate
marker, a drifted endpoint pin) passes the manifest choke point and is only
caught — if at all — at deploy (cycles 8-9).

## Suggestion
Add to `revolver/validation.py`:
- `@dataclass LaunchPlanReport` (fields: `ok: bool`, `no_op: bool`,
  `errors: list[str]`, and per-check booleans `nohup_ok`, `append_ok`,
  `endpoint_ok`, `budget_ok`, `one_pipeline_ok`).
- `check_launch_plan(plan: LaunchPlan, *, endpoint_pin: str | None = None)
  -> LaunchPlanReport` — pure, dry-run, stdlib-only; runs checks (a)-(e) below.
- `validate_manifest_launch(manifest: ProposalManifest, *, endpoint_pin: str |
  None = None) -> LaunchPlanReport` — delegates to `check_launch_plan` on
  `manifest.launch_plan`.
No I/O, no process launch.
