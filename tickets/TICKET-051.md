# TICKET-051 — RecurrenceReport + report (recurrence verdict)

Status: DONE
**Cycle:** 11 (Observe + report)
**Module:** `revolver/observe.py`

## Capability
Add `RecurrenceReport(failure_mode, recurred, cycles_done, cycles_in_flight, gaps,
outcomes, note)` dataclass +
`report(diagnosis, *, markers=None, read_cycles_out=None, read_trajectory=None) ->
RecurrenceReport`.

Compose the Cycle 10 marker observation (`observe`) with the trajectory outcomes
(`parse_trajectory_outcomes`) and the diagnosed `failure_mode` into a *recurrence
verdict*: did the diagnosed failure mode recur in the observed run?

## Invariants
- `recurred` is True when the observed run shows evidence the diagnosed failure mode
  re-occurred: a non-complete trajectory outcome (`max_steps_reached` / `error` / any
  value other than `exit:task_complete`), OR a gap where a done marker was expected
  (reported honestly, never assumed done — the §7 union rule), OR an in-flight cycle
  (started but not done).
- `recurred` is False (clean) only when every expected cycle is done AND every trajectory
  outcome is complete.
- The verdict is a pure, deterministic function of the inputs — it NEVER re-derives the
  diagnosis; the diagnosed `failure_mode` is reported verbatim.
- The expected cycles are the union of the diagnosis's `cycles_started` / `cycles_done` /
  `cycles_in_flight` (first-seen order).
- `markers` / `read_cycles_out` / `read_trajectory` are overridable seams (defaults: real
  file reads).
- READ-ONLY: no process launch, no process kill, no write; the only I/O is through the
  seams. Pure, deterministic, stdlib-only.

## Acceptance
- `report` over: clean run -> recurred False; failure-mode recurrence (non-complete
  outcome / gap / in-flight) -> recurred True; gaps feed the verdict; empty inputs;
  custom markers / read_cycles_out / read_trajectory seams; failure_mode reported
  verbatim; to_dict/from_dict round-trip.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
