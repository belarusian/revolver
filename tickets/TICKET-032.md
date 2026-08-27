# TICKET-032: cycles_out_append must be a non-empty append marker ending in newline — no truncate form

## Title
`cycles_out_append` must be a non-empty append marker ending in `\n`, and must
never be a truncate/overwrite form; nothing validates this.

## Evidence
- `revolver/launch_plan.py:185` sets
  `cycles_out_append = f"= LAUNCH {proposal.pipeline_id} {d.failure_mode} =\n"`
  — a bare marker line; it carries no redirect operator at all, so a validator
  cannot yet distinguish an append (`>>`) from a truncate (`>`).
- `LaunchPlan.validate()` (launch_plan.py:97-131) checks budgets and flags but
  never inspects `cycles_out_append` for a truncate form or a missing trailing
  newline.
- Grounding (four repo): `JUNIOR.md` §7 scar table — "Continuation launch reused
  a filename with `>` → truncated prior cycle markers ... Rule: Append (`>>`) or
  segment on continuation launches." `pipelines/v2/run-cycles.sh:36` uses
  `} >> "$OUT" 2>&1` (append); the counter-example at `run-cycles.sh:7` and
  `archive/deepseek-deharness-ts/run-cycles.sh:4` shows the truncate form `>
  cycles.out`.

## Impact
A `cycles_out_append` that is empty (non-no-op), lacks a trailing newline, or
encodes a truncate (`> cycles.out`) would wipe prior cycle markers on launch —
the exact scar in `JUNIOR.md` §7. The observer can only union what the launch
preserved, so a truncate silently destroys the gate-observer's input.

## Suggestion
In `check_launch_plan`, for a non-no-op plan:
- require `plan.cycles_out_append` to be non-empty;
- require it to end with `"\n"`;
- reject any truncate/overwrite form: flag if the marker (or an associated
  redirect) contains a single `>` not preceded by `>` (i.e. `> ` but not `>> `).
Record `append_ok` and an error string on violation.
