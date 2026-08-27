# TICKET-049: observe() — done vs started distinction feeds the later recurrence verdict

Status: OPEN
Date: 2026-08-27
Cycle: 10 synthesis audit
Target: `revolver/observe.py` (NEW module) — done/started semantics.

## Title
The observer must distinguish `done` (the `========== CYCLE N done ==========`
marker, JUNIOR.md §8 "Done") from `started` (a bare `========== CYCLE N
=========` marker, in-flight). This distinction feeds the "in-flight" report and
the later "did the diagnosed failure mode recur" verdict (cycles 11-12).

## Evidence
- JUNIOR.md §8 "Done" = `========== CYCLE N done ==========` in cycles.out AND no
  run-cycles/run*.py process AND the expected merge commits on main. The marker
  half is what the observer sees; a cycle is *done* only on the done marker.
- A bare `========== CYCLE N ==========` is *started* (in-flight) — it means the
  cycle began but has not yet emitted its done marker.
- Cycles 11-12 (the report half) will use cycles_done vs cycles_in_flight to decide
  whether the diagnosed failure mode recurred; the done/started split must be
  correct and stable.

## Impact
If done and started are conflated, the observer cannot tell a completed cycle from
an in-flight one, and the recurrence verdict (cycles 11-12) is meaningless. The
split is the foundation of the report phase.

## Suggestion
- A done marker sets status="done"; a bare start marker sets status="started".
- A cycle that has both a started and a done marker is done (done wins).
- A cycle with only a started marker is in-flight.
- The distinction is preserved in CycleMarker.status and surfaced in
  Observation.cycles_done / cycles_in_flight.
- Pure, deterministic, stdlib-only.
