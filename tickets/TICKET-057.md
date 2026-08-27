# TICKET-057 — render_final_report + FinalReport (compose the three observations)

## Capability
`FinalReport(failure_mode, recurred, observation, outcomes, git, note)` dataclass + `render_final_report(diagnosis, *, markers=None, read_cycles_out=None, read_trajectory=None, merge_commits=None, read_git_log=None) -> FinalReport`.

## Spec
- Compose the Cycle 10 marker observation (`observe`) + the Cycle 11 trajectory outcomes + recurrence verdict (`report`) + the Cycle 12 git observation (`observe_git`) into a single report.
- `recurred` is the Cycle 11 recurrence verdict — REUSED, NOT re-derived.
- `observation` = the Cycle 10 `Observation`; `outcomes` = the Cycle 11 `list[TrajectoryOutcome]`; `git` = the Cycle 12 `GitObservation`.
- The expected cycles are the union of the diagnosis's `cycles_started`/`cycles_done`/`cycles_in_flight` (first-seen order) — same derivation as `report`.
- Pure, deterministic, stdlib-only; READ-ONLY.

## Acceptance
- clean run -> recurred False; recurrence -> recurred True; git missing feeds the report; empty inputs; custom markers/read_cycles_out/read_trajectory/merge_commits/read_git_log seams.
