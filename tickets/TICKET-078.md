# TICKET-078 — Execute-not-grep replay tests: replay the generated artifacts, not their prose

**Status:** TODO
**Cycle:** 19
**Build Order row:** Derive-by-reference (17–19)

## Capability
Replace the docstring-grep replay tests (`test_runner_and_spoke_carry_one_line_import_delta`,
`test_every_file_carries_docstring` et al.) with tests that EXECUTE the proposal:
1. Build each class's proposal from the pinned predecessors (temp-dir fixtures for unit
   tests; one execution-plane test that reads the real triple via `triple.resolve` and
   skips off-plane).
2. `py_compile` every generated `.py` file.
3. Import-resolution: exec/import the generated runner in a namespace where the staged
   chat-model module satisfies its import (the reference chain resolves against the
   staged set, proving the emitted import points at the staged file, not a re-typed body).
4. Generated driver: parse `RUN=`/`SPOKE=` lines; assert they point at the STAGED paths;
   assert endpoints verbatim and `FIVE_REQUEST_TIMEOUT >= outer wall`.
5. Diff isolation: for every generated file, `difflib` diff vs its predecessor ==
   exactly the instruction's stated lines (byte-identity of everything else by
   construction — the law is checked, not asserted in prose).
6. Recurrence semantics (keep the good part of the current replay tests): the v4-shape
   guard still re-invokes over a seeded stale trajectory; the inner-wall variant differs
   from its predecessor ONLY in `--inner-seconds`.

## Acceptance
- The replaced grep tests are GONE (replaced, not extended — the fiction-testing greps
  that passed over non-runnable artifacts are removed in the same PR that adds the
  executing tests; test count may net-drop only if a removed grep-test's semantics are
  fully covered by an executing test — state the mapping in the log block).
- A deliberately broken instruction (wrong replacement text) makes the proposal fail at
  derive time (compile/diff isolation), and the test proves it.
- CI-safe: execution-plane-dependent tests skip when the triple paths are absent
  (GitHub lens), run fully on Sunny; stdlib only, no endpoints, no wall-clocks.
- Gate: pytest + ruff + mypy clean; log block cites which old grep tests each new
  executing test replaces.
