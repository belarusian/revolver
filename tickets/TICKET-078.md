# TICKET-078 — Execute-not-grep replay tests: replay the generated artifacts, not their prose

**Status:** DONE
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

## Resolution (Cycle 39)
Verified against the current `tests/test_replay.py` (23 tests, all on main at
f0cbf13) and flipped TODO -> DONE on its own evidence. No new code and no new
tests were added this cycle — this is a verification + flip pass.

Each acceptance bullet is met by the EXECUTING tests already on main:

- **Compile** — `test_all_py_files_compile` (and the per-class
  `test_all_py_files_compile` variants) `py_compile` every generated `.py` file.
- **Import-resolution** — `test_import_resolution` execs the generated runner in a
  namespace where the staged chat-model module satisfies its import, proving the
  emitted import points at the staged file, not a re-typed body.
- **Diff isolation** — `test_diff_isolation` (and the per-class variants) take a
  `difflib` diff of every generated file vs its predecessor and assert it equals
  exactly the instruction's stated lines (byte-identity of everything else).
- **Broken-instruction fails at derive** — `test_broken_instruction_fails_at_derive`
  feeds a wrong replacement text and proves the proposal fails at derive time
  (compile/diff isolation), not at replay time.
- **Recurrence semantics** — `test_v4_reader_reinvokes_on_stale` re-invokes the
  v4-shape guard over a seeded stale trajectory (the good part of the old replay
  tests, kept).

The docstring-grep FICTION tests (`test_every_file_carries_docstring` et al.) are
GONE from `tests/test_replay.py` — replaced, not extended. The one same-named test
that survives, `test_runner_and_spoke_carry_one_line_import_delta` in
`tests/test_fixes_generators.py` (TICKET-086), is a REAL diff-isolation test (reads
the predecessor, asserts exactly one line deleted + one added), NOT a prose-grep.

CI-safe: execution-plane-dependent tests carry the `requires_triple` skip marker
(`pytest.mark.skipif(not _triple_available(), ...)` at `tests/test_replay.py:51`,
with `_TRIPLE_DIR = Path.home()/"AI"/"revolver"/"triple"` at :43) — they skip when
the triple dir is absent (GitHub lens) and run fully on Sunny.
