# TICKET-099: `tickets/TICKET-090.md` stale cross-reference — "TICKET-087 stays OPEN"

Status: DONE
Cycle: 40 (synthesis audit)

## Purpose
`tickets/TICKET-090.md` line 28 still asserts that `build_inner_wall_fix`
"(TICKET-087 stays OPEN — documented design fact)". That is stale: TICKET-087 was
resolved in Cycle 34 (PR #123) and `build_inner_wall_fix` IS now registered in
`FIX_BUILDERS` and reachable via `propose()`. The ticket text contradicts the
current code and the DONE status of TICKET-087.

## Evidence
`tickets/TICKET-090.md:28`:

    NOT changed: generated content, the four ChangeInstruction objects, derive() calls,
    the FIX_BUILDERS registry, and `build_inner_wall_fix` (TICKET-087 stays OPEN —
    documented design fact).

Contradicted by:
1. `tickets/TICKET-087.md:3` — `**Status:** DONE` (resolved Cycle 34).
2. `revolver/fixes.py:574` — `"inner-wall": build_inner_wall_fix` (registered).
3. `revolver/fixes.py:564` — comment: "The inner-wall builder is registered: its
   predecessor_driver is now optional".
4. `tests/test_fixes_generators.py` — `test_registered_in_fix_builders` asserts the
   registration.

## Impact
- A reader of TICKET-090 is told a design fact that is no longer true, which
  misrepresents the reachability of the inner-wall repair path.
- It is the only remaining "stays OPEN" reference in `tickets/` (verified by
  `grep -rn "stays OPEN" tickets/*.md` returning only this line).

## Suggestion
Edit `tickets/TICKET-090.md:28` to reflect the current state: `build_inner_wall_fix`
was NOT changed by the client-timeout fix, and TICKET-087 (which later made it
reachable via `propose()`) is now DONE. Docs/ticket-only change; no test impact.

## Resolution (Cycle 40)
Updated `tickets/TICKET-090.md:28`: replaced the stale "(TICKET-087 stays OPEN —
documented design fact)" with a note that `build_inner_wall_fix` was not changed by
the client-timeout fix and that TICKET-087 (which later registered it in
`FIX_BUILDERS` and made it reachable via `propose()`) is now DONE. Ticket-only change;
no test impact. Verified `grep -rn "stays OPEN" tickets/*.md` returns nothing.
