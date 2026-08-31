# TICKET-101: `docs/API.md` `build_outer_freshness_fix` signature missing the `triple_dir` seam

Status: DONE
Cycle: 53 (synthesis audit — steady-state maintenance verification)
Parent: TICKET-100

## Evidence

`docs/API.md:151` (before fix):

    def build_outer_freshness_fix(diagnosis: Diagnosis, *, predecessor_runner: str) -> list[NewFile]: ...

Contradicted by `revolver/fixes.py:475-481` (current):

    def build_outer_freshness_fix(
        diagnosis: Diagnosis,
        *,
        predecessor_runner: str,
        triple_dir: str | Path | None = None,
    ) -> list[NewFile]:

The keyword-only `triple_dir: str | Path | None = None` seam was added by
TICKET-100 (commit dc8ec20, "fix: add keyword-only triple_dir seam to
build_outer_freshness_fix (TICKET-100) (#136)"). The sibling builder
`build_client_timeout_fix` already shows the seam in `docs/API.md:149`, so the
outer-freshness row was the only one left stale after TICKET-100 landed.

## Impact
- A reader of the API reference is given a signature that does not match the
  code: the documented call shape omits the `triple_dir` seam, so a caller
  following the docs would not know the builder can be pointed at a fixture
  triple dir (the exact testability capability TICKET-100 added).
- The API reference is the single source of truth for the public surface; a
  stale signature is a steady-state drift that compounds on every re-read.

## Suggestion
Update `docs/API.md:151` to include the keyword-only seam, matching the code
and the sibling row at line 149:

    def build_outer_freshness_fix(diagnosis: Diagnosis, *, predecessor_runner: str, triple_dir: str | Path | None = None) -> list[NewFile]: ...

Docs-only change; no test impact.

## Resolution (Cycle 53)
Updated `docs/API.md:151` to
`def build_outer_freshness_fix(diagnosis: Diagnosis, *, predecessor_runner: str, triple_dir: str | Path | None = None) -> list[NewFile]: ...`.
Verified the signature now matches `revolver/fixes.py:475-481` and is consistent
with the sibling `build_client_timeout_fix` row at `docs/API.md:149`. Docs-only
change; gate re-measured green (415 passed / ruff clean / mypy clean, 14 files).
