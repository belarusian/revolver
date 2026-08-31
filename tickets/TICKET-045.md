# TICKET-045: parse_cycle_markers() — per-cycle marker parsing (file order)

Status: DONE
Date: 2026-08-27
Cycle: 10 synthesis audit
Target: `revolver/observe.py` (NEW module) — the observer half of the loop.

## Title
`revolver/observe.py` does not exist on main. Add
`CycleMarker(cycle, status, raw)` + `parse_cycle_markers(text, *, done_pattern=None)
-> list[CycleMarker]`: parse the `cycles.out` text into per-cycle markers, in file
order.

## Evidence
- No `revolver/observe.py` on main (`ls revolver/` shows deploy.py, diagnosis.py,
  fixes.py, launch_plan.py, manifest.py, proposal.py, relaunch.py, sentry_client.py,
  sentry_pin.py, validation.py only). Cycles 8-9 landed deploy + relaunch; cycle 10
  begins the observe + report phase (Build Order cycles 10-12).
- JUNIOR.md §8 "Done" = `========== CYCLE N done ==========` in cycles.out. A bare
  `========== CYCLE N ==========` (no "done") is a started/in-flight marker.
- JUNIOR.md §1: "the gate log ... append-only ground truth — position is the only
  order; never reorder, never rewrite". The observer must return markers in file
  order, never reordered or deduped by cycle number (a cycle may appear more than
  once across restarts).
- `revolver/diagnosis.py::parse_raw_artifacts` already has `_RE_DONE`/`_RE_START`
  regexes but aggregates into *sets* (sorted, deduped). The observer needs the finer
  per-marker list (position-preserving), a distinct capability.

## Impact
Without per-cycle marker parsing, the observer cannot distinguish done from
in-flight, cannot report gaps honestly, and cannot preserve file order (the only
order). The `observe()` report (TICKET-046) and the later failure-mode-recurrence
verdict (cycles 11-12) depend on this.

## Suggestion
`CycleMarker(cycle: int, status: str, raw: str)` dataclass (status in
{"done", "started"}). `parse_cycle_markers(text, *, done_pattern=None) ->
list[CycleMarker]`:
- Scan `text` line by line; a line matching the done marker -> `CycleMarker(n,
  "done", line)`; a line matching the bare start marker (not done) ->
  `CycleMarker(n, "started", line)`.
- `done_pattern` is an overridable seam (default: the §8 done-marker regex) so tests
  inject a custom dialect.
- Returns markers in file order (position is the only order); never reorder, never
  dedupe.
- Empty text -> empty list.
- Pure, deterministic, stdlib-only; no I/O.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 35.
