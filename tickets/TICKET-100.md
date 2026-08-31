# TICKET-100: `build_outer_freshness_fix` hardcodes triple path with no overridable seam (unit-test blocker)

Status: DONE
Cycle: 42 (synthesis audit)
Parent: TICKET-090
Issue: #135

## Evidence

`revolver/fixes.py` line 513 (current):
`triple_dir = Path.home() / "AI" / "revolver" / "triple"` — hardcoded, so the
outer-freshness builder can only be exercised against the real execution-plane
triple dir. This is the exact testability gap TICKET-090 fixed for
`build_client_timeout_fix` (which now takes a keyword-only
`triple_dir: str | Path | None = None` seam, `revolver/fixes.py:262`).

The outer-freshness builder also ignores its `predecessor_runner` parameter
(`revolver/fixes.py:508` — `_ = predecessor_runner`), retained only for signature
compatibility.

## Inconsistency

- `build_client_timeout_fix(diagnosis, *, triple_dir=None)` — has the seam
  (TICKET-090, DONE).
- `build_outer_freshness_fix(diagnosis, *, predecessor_runner)` — NO seam; hardcodes
  the triple path and ignores `predecessor_runner`.

`tests/test_replay.py::TestOuterFreshnessReplay` calls the builder directly
(e.g. `build_outer_freshness_fix(_cycle16_diagnosis(), predecessor_runner="PRE")`)
and is NOT `@requires_triple`-guarded, so it depends on the real triple dir being
present — the same class of testability gap TICKET-090 closed for client-timeout.

## Impact
- The outer-freshness repair path cannot be unit-tested against a fixture triple
  dir (no `triple_dir` seam), so its tests are coupled to the local execution-plane
  `triple/` dir (absent on CI runners — the documented `test_replay.py`
  FileNotFoundError).
- Inconsistent with the sibling builder's API.

## Suggestion
Mirror TICKET-090: add a keyword-only `triple_dir: str | Path | None = None` seam to
`build_outer_freshness_fix`; when `None` resolve to the canonical
`Path.home() / "AI" / "revolver" / "triple"` (existing behavior preserved exactly).
Replace the hardcoded line with
`triple_dir = Path(triple_dir) if triple_dir is not None else Path.home() / "AI" / "revolver" / "triple"`.
The two `*_pred = triple_dir / "..."` lines are unchanged. Add a
`TestOuterFreshnessTripleDirSeam` test that builds a temp dir with the two
predecessor files (`outer_freshness_run_v3.py`, `outer_freshness_driver_v3.sh`)
containing the exact target strings the builder replaces, then calls
`build_outer_freshness_fix(d, triple_dir=tmp_path)` and asserts the 2 NewFiles are
produced under PROPOSAL_NAMESPACE — runs WITHOUT `@requires_triple`, deterministic.

## Resolution (Cycle 42)
Added the keyword-only `triple_dir: str | Path | None = None` seam to
`build_outer_freshness_fix` (mirroring TICKET-090). When `None` it resolves to the
canonical `Path.home() / "AI" / "revolver" / "triple"` (existing behavior preserved
exactly); the two `*_pred = triple_dir / "..."` lines are unchanged. Updated the
docstring to document the seam. Added
`TestOuterFreshnessTripleDirSeam::test_triple_dir_seam_produces_two_new_files` in
`tests/test_replay.py` — builds a temp dir with the two predecessor files containing
the exact target strings, calls `build_outer_freshness_fix(d, predecessor_runner="PRE",
triple_dir=tmp_path)`, and asserts the 2 NewFiles are produced under
PROPOSAL_NAMESPACE with the temp-dir predecessor named in the derived header (proves
the seam is honored even when the real triple dir is present locally). Runs WITHOUT
`@requires_triple`, deterministic.

Gate (Rule 3, re-measured on the branch):

| Check | Result |
|---|---|
| pytest tests/ -x -q | 415 passed |
| ruff check revolver/ | All checks passed! |
| mypy revolver/ --ignore-missing-imports | no issues found in 14 source files |
