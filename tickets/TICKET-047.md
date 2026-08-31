# TICKET-047: observe() tests — parse_cycle_markers + observe over every seam

Status: DONE
Date: 2026-08-27
Cycle: 10 synthesis audit
Target: `tests/test_observe.py` (NEW test module).

## Title
Add `tests/test_observe.py` covering `parse_cycle_markers` and `observe` with
injectable seams / `patch.object` — never constructor-level patches; never touch the
real filesystem.

## Evidence
- The briefing's explicit acceptance criteria: `parse_cycle_markers` (done marker,
  started marker, mixed, out-of-order preserved in file order, custom done_pattern
  seam, empty text). `observe` (all done, some in-flight, gaps reported honestly,
  empty cycles, custom markers seam, read_cycles_out seam).
- Rule 4: use `patch.object(instance, 'method')`, not constructor-level patches.
- Cycles 8-9 established the seam-test pattern (test_deploy.py, test_relaunch.py):
  inject fakes so nothing touches the real filesystem or spawns a real process.

## Impact
Without tests, the observer's honest-gap behavior and file-order preservation are
unverified — exactly the two properties the §7 scar and §1 "position is the only
order" rule demand. The gate (pytest) must prove them.

## Suggestion
`tests/test_observe.py`:
- parse_cycle_markers: done marker -> CycleMarker(n,"done",raw); started marker ->
  CycleMarker(n,"started",raw); mixed text; out-of-order input preserved in file
  order (NOT sorted); custom done_pattern seam (inject a different dialect); empty
  text -> [].
- observe: all done; some in-flight (started but not done); gaps reported honestly
  (a cycle with no marker is a gap, not assumed done); empty cycles -> empty
  Observation; custom markers seam (inject a list[CycleMarker]); read_cycles_out
  seam (inject a fake reader, default never called).
- Use injectable seams / patch.object; never touch the real filesystem.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 35.
