# TICKET-095: Remove dead embedded module body `_outer_freshness_runner_content` from `revolver/fixes.py`

Status: DONE
Cycle: 37 (synthesis audit)

## Purpose
`revolver/fixes.py` must carry ZERO embedded module bodies. The derive-by-reference
procedure (Cycle 17-19, `revolver/derive.py`) replaced value-embedding generators:
each fix builder now composes `ChangeInstruction` objects and calls `derive()`, which
reads the predecessor by PATH and emits a NEW versioned file. One pre-derive leftover
still embeds a full module body as a string-concatenated value:
`_outer_freshness_runner_content`. It is dead and must be removed.

## Evidence
- `revolver/fixes.py:477` — `def _outer_freshness_runner_content(evidence: str) -> str:`
  spans lines 477-577 (ends `return doc + body` at :577). Its body is a 101-line
  string-concatenation of a complete Python module (imports, `_max_seq`,
  `pass_freshness_guard`, `read_newest_trajectory`, `main`) — i.e. an embedded
  module body, the exact anti-pattern `revolver/derive.py:4-9` says derive-by-reference
  replaces.
- It is NEVER called. `grep -rn _outer_freshness_runner_content` returns only its own
  `def` (revolver/fixes.py:477) plus stale bytecode (`revolver/__pycache__/fixes.*.pyc`).
  No caller in `revolver/`, `tests/`, or `docs/`.
- The live path is `build_outer_freshness_fix` (revolver/fixes.py:580), which does NOT
  call it: it composes two `ChangeInstruction` objects (runner_instr :626, driver_instr
  :647) and calls `derive()` (runner :644, driver :654). The runner's step-2 guard is
  now expressed as a `ChangeInstruction.replacement` (lines 629-640), not as an
  embedded body.
- It is the ONLY embedded module body in the module. The other content helpers,
  `_content` (:41) and `_marker_content` (:58), assemble a docstring + a few plan/marker
  lines — small snippets, not module bodies. Removing :477-577 leaves ZERO embedded
  module bodies.

## Impact
- Violates the module's stated invariant (derive-by-reference; no value-embedding
  generators). A reader sees a full module body and assumes it is the live output,
  when the live output is produced by `derive()` from the triple predecessor.
- 101 lines of dead, untested, un-reachable code that drifts from the real run-v3.py
  (e.g. the embedded body's `read_newest_trajectory`/`_max_seq` are re-implementations
  that no longer match the predecessor the builder actually derives from).
- Misleads the "thin instruction emitter" contract: the module appears to still embed
  a body, contradicting the three builders' derive-only design.

## Suggestion
Delete `revolver/fixes.py` lines 477-579 (the function plus its two trailing blank
lines) so `build_outer_freshness_fix` (:580) follows `_outer_freshness_evidence`
(:460-474) with normal spacing. No caller changes. Re-run
`pytest tests/test_fixes_generators.py tests/test_replay.py -q` (the outer-freshness
replay tests exercise `build_outer_freshness_fix`, which is untouched) and
`ruff check revolver/` (F841/unused should stay clean).

DONE (Cycle 37): `_outer_freshness_runner_content` (fixes.py:477-578) removed; `revolver/fixes.py` now carries ZERO embedded module bodies. Gate clean (414 passed, ruff clean, mypy clean). See TICKET-077.
