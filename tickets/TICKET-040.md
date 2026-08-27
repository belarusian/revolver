# TICKET-040: first_not_done_cycle() — resume-point derivation (R1)

Status: OPEN
Date: 2026-08-27
Cycle: 9 synthesis audit
Target: `revolver/relaunch.py` (NEW module) — driver relaunch from the first not-done cycle.

## Title
`revolver/relaunch.py` does not exist on main. Add the pure resume-point
derivation `first_not_done_cycle(cycles, *, done=None) -> int | None`: the smallest
cycle number in `cycles` that is NOT in `done` (the resume point).

## Evidence
- No `revolver/relaunch.py` on main (`ls revolver/` shows deploy.py, diagnosis.py,
  fixes.py, launch_plan.py, manifest.py, proposal.py, sentry_client.py, sentry_pin.py,
  validation.py only). Cycle 8 landed `revolver/deploy.py` (commit b87ab76); cycle 9
  is the relaunch-from-first-not-done phase.
- JUNIOR.md §8 stall rescue step 3: "Driver dead (no process) -> relaunch from the
  FIRST not-done cycle; Phase 0 repairs leftovers." This is the resume rule the
  function encodes.
- JUNIOR.md §7 scar (B1): "3600s wall SIGALRM'd a cycle that had shipped an hour of
  work — stranded branch + open issues, no PR" -> rule "B1 wall sizing + R1 Phase-0
  resume". R1 = resume from the first not-done cycle, not from 1.
- `revolver/diagnosis.py::Diagnosis` already carries `cycles_done: list[int]`
  (and `cycles_started`, `cycles_in_flight`, `cycles_wall_kill`) — the natural default
  source for the `done` set.

## Impact
Without a deterministic resume-point derivation, a relaunch either restarts from cycle
1 (re-doing shipped work — the B1 scar) or has no well-defined start. The whole
relaunch plan (TICKET-041) and its verification (TICKET-042) depend on this value.

## Suggestion
`first_not_done_cycle(cycles, *, done=None) -> int | None`:
- `cycles`: an iterable of cycle numbers (may be out of order, may contain duplicates).
- `done`: an overridable seam — a set/collection of cycle numbers already done. When
  `None`, default to `set(cycles)` is WRONG; instead the caller supplies `done` (e.g.
  `set(diagnosis.cycles_done)`). The seam exists so tests inject `done` directly.
- Returns the smallest cycle number in `cycles` that is NOT in `done`.
- All-done (every cycle in `cycles` is in `done`) -> `None`.
- Empty `cycles` -> `None`.
- Out-of-order / duplicate input handled: sort and dedupe before scanning.
- Pure, deterministic, stdlib-only; no I/O, no process.
