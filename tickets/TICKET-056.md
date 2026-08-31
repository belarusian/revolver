# TICKET-056 — observe_git + GitObservation (honest merge-commit reporting)

Status: DONE
## Capability
`GitObservation(cycles_merged, cycles_missing, note)` dataclass + `observe_git(cycles, *, merge_commits=None, read_git_log=None) -> GitObservation`.

## Spec
- Report which of the expected `cycles` have the expected merge commit (`cycles_merged`) and which are *missing* (`cycles_missing`) — reported honestly, never assumed merged (the §7 union rule).
- `merge_commits` and `read_git_log` are overridable seams. `read_git_log` default: a real git log read (the §8 "Done" merge-commit half); only consulted when `merge_commits` is None.
- `cycles_merged` / `cycles_missing` partition `cycles` in the input's order.
- READ-ONLY: no process launch, no process kill, no write. Pure, deterministic, stdlib-only.

## Acceptance
- all merged, some missing, empty cycles, custom merge_commits/read_git_log seams, injected reader means default never called.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
