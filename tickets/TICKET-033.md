# TICKET-033: endpoint_pin must be verbatim vs expected (default self-consistency)

## Title
`check_launch_plan` must verify `plan.endpoint_pin` is verbatim against an
expected pin, defaulting to self-consistency when no pin is supplied.

## Evidence
- `revolver/launch_plan.py:167` (no-op) and line 194 (actionable) both set
  `endpoint_pin=d.endpoint_pin` — the plan's pin is copied verbatim from the
  `Diagnosis` (`revolver/diagnosis.py:73`, `endpoint_pin: str = ""`).
- The command string embeds the pin at launch_plan.py:182 (`--endpoint
  {d.endpoint_pin}`), so a pin that drifts between the `Diagnosis`, the plan
  field, and the command would be undetected.
- `grep -rn "endpoint_pin" revolver/validation.py` returns nothing — no
  validator compares the plan's pin to an expected value.
- Grounding (four repo): `JUNIOR.md` §3 endpoint table — "Never touch an
  endpoint not in your brief. One pipeline per endpoint at a time."

## Impact
A `LaunchPlan` whose `endpoint_pin` does not match the pin the pipeline is
actually pinned to (or that appears in its own command) would launch against the
wrong endpoint — violating the one-pipeline-per-endpoint allocation and risking a
litellm timeout or an out-of-brief endpoint.

## Suggestion
In `check_launch_plan(plan, *, endpoint_pin=None)`:
- if `endpoint_pin is None`: assert self-consistency — `plan.endpoint_pin` must
  be non-empty and must appear verbatim in `plan.command` (the `--endpoint`
  token).
- if `endpoint_pin` is given: require `plan.endpoint_pin == endpoint_pin`
  (verbatim, no normalization).
Record `endpoint_ok` and an error string on mismatch.
