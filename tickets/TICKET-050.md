# TICKET-050 — TrajectoryOutcome + parse_trajectory_outcomes (file order, never reorder/dedupe)

Status: DONE
**Cycle:** 11 (Observe + report)
**Module:** `revolver/observe.py`

## Capability
Add `TrajectoryOutcome(cycle, outcome, raw)` dataclass +
`parse_trajectory_outcomes(text, *, read_trajectory=None) -> list[TrajectoryOutcome]`.

Parse the outer's per-cycle trajectory JSON — the `{"outcome": ..., "messages": [...]}`
object (or a JSON array of such objects) the outer reads after each cycle (JUNIOR.md §1,
run.py step 2) — into per-cycle outcomes. The `outcome` field is the terminal signal
(`exit:task_complete` on success; `max_steps_reached` / `error` on failure). The observer
reads the *outcome* (not the messages — the messages are the spoke's private transcript).

## Invariants
- Returns outcomes in FILE ORDER (position is the only order — never reordered, never
  deduped; a cycle may have more than one trajectory across restarts).
- `cycle` is the 1-based position of the object in the array (or 1 for a single object) —
  the §1 dialect carries no explicit cycle number.
- `read_trajectory` is an overridable seam (default: a real file read of the newest
  trajectory) so tests inject a fake without touching the filesystem.
- Malformed JSON, empty text, or a non-object/non-array payload -> empty list (never
  raises).
- Completeness is derived, not stored: `exit:task_complete` is the only complete outcome;
  `max_steps_reached` / `error` / any other value are non-complete.
- Pure, deterministic, stdlib-only; READ-ONLY (no process launch/kill/write).

## Acceptance
- `parse_trajectory_outcomes` over: single object, JSON array, empty, malformed -> empty,
  non-object/non-array -> empty, object without `outcome` key, custom `read_trajectory`
  seam, file order preserved, no reorder/dedupe.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
