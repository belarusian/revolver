# TICKET-098: `docs/API.md` `revolver.fixes` section is stale (signatures + registry note)

Status: DONE
Cycle: 37 (synthesis audit)

## Purpose
The `revolver.fixes` section of `docs/API.md` (lines 140-156) shows signatures and a
registry note that no longer match the code after TICKET-087 (inner-wall reachable via
`propose()`) and TICKET-090 (client-timeout `triple_dir` seam). The docs should match
the three fix-class builders this audit verifies.

## Evidence
`docs/API.md:149-156`:

    def build_client_timeout_fix(diagnosis: Diagnosis) -> list[NewFile]: ...
    def build_inner_wall_fix(diagnosis: Diagnosis, *, predecessor_driver: str) -> list[NewFile]: ...
    def build_outer_freshness_fix(diagnosis: Diagnosis, *, predecessor_runner: str) -> list[NewFile]: ...

    Note: `build_inner_wall_fix` and `build_outer_freshness_fix` are **not** in
    `FIX_BUILDERS` (they take a keyword-only predecessor argument); they are called
    directly with the predecessor text.

Stale against the code:
1. `build_client_timeout_fix` (docs :149) omits the `triple_dir` seam added in
   TICKET-090. Actual signature `revolver/fixes.py:259-263`:
   `build_client_timeout_fix(diagnosis, *, triple_dir: str | Path | None = None)`.
2. `build_inner_wall_fix` (docs :150) shows `predecessor_driver: str` (required).
   Actual `revolver/fixes.py:348-352`: `predecessor_driver: str | None = None`
   (optional; falls back to `diagnosis.inner_wall_driver_path`, TICKET-087).
3. The registry note (docs :154-156) says `build_inner_wall_fix` is **not** in
   `FIX_BUILDERS`. It IS: `revolver/fixes.py:679`
   (`"inner-wall": build_inner_wall_fix`). Only `build_outer_freshness_fix` is absent
   (it is not in the single-arg registry; `revolver/fixes.py:668-673`).

## Impact
- A newcomer reading `docs/API.md` is told `build_inner_wall_fix` cannot be reached via
  `propose()`/`FIX_BUILDERS`, which is false (TICKET-087, Cycle 34, PR #123) and is
  asserted by `tests/test_fixes_generators.py:384-389`
  (`test_registered_in_fix_builders`).
- The client-timeout signature is missing its documented seam, so the docs understate
  the testability contract (TICKET-090).

## Suggestion
Update `docs/API.md:149-156`:
- `build_client_timeout_fix(diagnosis: Diagnosis, *, triple_dir: str | Path | None = None)`.
- `build_inner_wall_fix(diagnosis: Diagnosis, *, predecessor_driver: str | None = None)`.
- Registry note: only `build_outer_freshness_fix` is not in `FIX_BUILDERS` (keyword-only
  `predecessor_runner`, called directly); `build_inner_wall_fix` IS registered
  (`"inner-wall"`) and reachable via `propose()`.
Docs-only change; no test impact.

## Resolution (Cycle 38)
Updated `docs/API.md` revolver.fixes section: `build_client_timeout_fix` now shows the
`triple_dir: str | Path | None = None` seam; `build_inner_wall_fix` now shows
`predecessor_driver: str | None = None`; registry note corrected to state that only
`build_outer_freshness_fix` is absent from `FIX_BUILDERS` while `build_inner_wall_fix`
is registered (`"inner-wall"`) and reachable via `propose()`. Docs-only change; no test
impact.
