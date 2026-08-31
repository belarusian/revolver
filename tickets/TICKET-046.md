# TICKET-046: observe() — honest gap reporting (observer unions what the launch preserved)

Status: DONE
Date: 2026-08-27
Cycle: 10 synthesis audit
Target: `revolver/observe.py` (NEW module) — the observer half of the loop.

## Title
Add `Observation` dataclass (cycles_seen, cycles_done, cycles_in_flight, gaps, note)
+ `observe(cycles, *, markers=None, read_cycles_out=None) -> Observation`: given the
ordered list of cycle numbers the driver is responsible for and the parsed markers,
report which are done, which are in-flight, and which are *gaps* — reported
honestly.

## Evidence
- JUNIOR.md §7 scar: "Continuation launch reused a filename with `>` -> truncated
  prior cycle markers; run_health NO-GO'd on a gap that was an operator typo, not a
  real miss" -> rule "Observer unions `cycles*.out` and reports honestly when
  markers are truly absent". A cycle that is neither seen nor done is a gap; the
  observer must NOT assume it is done.
- JUNIOR.md §8: "the gate log stays the source of truth; `cycles.out` is the
  observer's input, and the observer can only union what the launch preserved."
- `revolver/relaunch.py::verify_relaunch` already uses an overridable
  `read_cycles_out` seam (default real file read) — the observer reuses the same
  seam pattern so it stays pure + testable.

## Impact
Without honest gap reporting, a truncated cycles.out (the §7 scar) would be silently
treated as "done" and the run would NO-GO on a phantom gap or, worse, pass on a real
miss. The observer is the read-only half of the loop; it must report what the data
says, not what is assumed.

## Suggestion
`Observation(cycles_seen, cycles_done, cycles_in_flight, gaps, note)` dataclass
(each a list[int], note a str) with `to_dict`/`from_dict`. `observe(cycles, *,
markers=None, read_cycles_out=None) -> Observation`:
- `cycles`: ordered list of cycle numbers the driver is responsible for.
- `markers`: overridable seam — a list[CycleMarker] (default: parse via
  `read_cycles_out`). `read_cycles_out`: overridable seam (default: real file read).
- cycles_done = cycles in `cycles` that have a "done" marker.
- cycles_in_flight = cycles in `cycles` that have a "started" marker but no "done"
  marker.
- cycles_seen = cycles in `cycles` that have any marker (done or started).
- gaps = cycles in `cycles` that have NO marker at all (neither seen nor done) —
  reported honestly, never assumed done.
- Pure logic; the only I/O is through the seams.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 35.
