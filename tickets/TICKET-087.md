# TICKET-087 — build_inner_wall_fix is not reachable via propose() (absent from FIX_BUILDERS)

**Status:** DONE
**Cycle:** 34 (resolved)
**Parent:** TICKET-069

## Evidence

`revolver/fixes.py` (pre-change, line 633-640): `build_inner_wall_fix` took a
keyword-only `predecessor_driver: str` with no default, so the single-arg
`builder(diagnosis)` registry (`FIX_BUILDERS`) could not call it. It was therefore
NOT registered, and `propose()` could not reach the inner-wall repair path. Two
tests asserted this negative design:
- `tests/test_fixes_generators.py::TestInnerWallContract::test_not_in_fix_builders_registry`
- `tests/test_fixes_generators.py::TestInnerWallContract::test_called_directly_with_keyword_only_predecessor_driver`

## Resolution (Cycle 34)

- Added an additive `Diagnosis.inner_wall_driver_path: str | None = None` field
  (round-trip safe via `to_dict`/`from_dict`).
- `build_inner_wall_fix(diagnosis, *, predecessor_driver: str | None = None)`:
  when `predecessor_driver` is `None` it falls back to
  `diagnosis.inner_wall_driver_path`; if that is also `None` it raises a clear
  `ValueError` (never silently emits a wrong file). Behavior is byte-identical
  when `predecessor_driver` IS supplied.
- Registered `"inner-wall": build_inner_wall_fix` in `FIX_BUILDERS`; updated the
  registry comment (the outer-freshness builder still is not registered).
- Updated `TestInnerWallContract`: replaced `test_not_in_fix_builders_registry`
  with `test_registered_in_fix_builders`; kept
  `test_called_directly_with_keyword_only_predecessor_driver` passing; added
  `test_reachable_via_propose` and
  `test_raises_value_error_when_no_predecessor_path`.
- Updated `tests/test_proposal.py::TestFixBuilders::test_registry_covers_all_modes`
  to include `"inner-wall"` in the expected key set.

Gate (Rule 3): 414 passed, ruff clean, mypy clean. Merged on main.
