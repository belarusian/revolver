# TICKET-090 — build_client_timeout_fix hardcodes triple path with no overridable seam (unit-test blocker)

**Status:** DONE
**Cycle:** 32 (synthesis audit) / 33 (resolved)
**Parent:** TICKET-069
**Issue:** #120
**PR:** #121

## Evidence

`revolver/fixes.py` line 278 (pre-fix):
`triple_dir = Path.home() / "AI" / "revolver" / "triple"` — hardcoded, so the
client-timeout builder could only be exercised against the real execution-plane
triple dir. The client-timeout tests in `tests/test_fixes_generators.py` were
`@requires_triple`-guarded and SKIP in CI (no triple dir on the runner).

## Fix (Cycle 33, PR #121)

- `build_client_timeout_fix(diagnosis, *, triple_dir: str | Path | None = None)` —
  new keyword-only seam. When `None` (default) it resolves to the canonical
  `Path.home() / "AI" / "revolver" / "triple"` (existing behavior preserved exactly).
- Replaced the hardcoded line with
  `triple_dir = Path(triple_dir) if triple_dir is not None else Path.home() / "AI" / "revolver" / "triple"`.
  The four `*_pred = triple_dir / "..."` lines are unchanged.
- Added module-level `from pathlib import Path` (annotation; ruff F821).
- Updated the docstring to document the seam.
- NOT changed: generated content, the four ChangeInstruction objects, derive() calls,
  the FIX_BUILDERS registry, and `build_inner_wall_fix` (TICKET-087 stays OPEN —
  documented design fact).

## Test

`TestClientTimeoutTripleDirSeam::test_triple_dir_seam_produces_four_new_files`
builds a temp dir with the four predecessor files (chat_model.py, run-v3.py,
cycle-implementation-v4.py, run-cycles-v3.sh) containing the exact target strings
the builder replaces, then calls `build_client_timeout_fix(d, triple_dir=tmp_path)`
and asserts the 4 NewFiles are produced under PROPOSAL_NAMESPACE. Runs WITHOUT
`@requires_triple` (no real triple dir needed), deterministic.

## Gate (Rule 3, re-measured on the branch)

| Check | Result |
|---|---|
| pytest tests/ -x -q | 412 passed |
| ruff check revolver/ | All checks passed! |
| mypy revolver/ --ignore-missing-imports | no issues found in 14 source files |
