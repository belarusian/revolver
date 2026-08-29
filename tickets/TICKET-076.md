# TICKET-076 — `revolver/derive.py`: predecessor-in, versioned-variant-out, verification by construction

**Status:** TODO
**Cycle:** 17
**Build Order row:** Derive-by-reference (17–19)

## Capability
The derive core. `derive(predecessor: Path | str, instruction: ChangeInstruction) -> DerivedVariant`:
- `ChangeInstruction` = dataclass (stdlib only): `kind` (e.g. `swap-import`,
  `insert-export`, `repoint-path`), `target` (line/regex to match), `replacement`
  (exact new text), `new_name` (versioned output filename), `evidence` (citation string).
  The instruction is DATA — the scar table becomes a vocabulary the machine composes.
- Read predecessor text READ-ONLY; apply exactly ONE stated minimal edit; emit NEW
  versioned content (never mutate the predecessor — hard rule 7).
- Generated docstring states: diff-from-predecessor (the one stated edit), the
  predecessor's PATH (reference — the version chain: run-vN names run-v(N−1), which
  names its own predecessor), and the evidence.
- Verification BY CONSTRUCTION, fail-loud: `py_compile.compile(doraise=True)` on the
  output (for `.py`), and `difflib` diff against the predecessor asserting the changed
  line set == exactly the instruction's stated lines. Any extra delta ⇒
  `DerivationError` — the proposal fails, nothing stages.
- Pure function of inputs: deterministic, no endpoints, no wall-clocks.

## Acceptance
- Derive over a temp-dir fixture predecessor (a 10-line stub runner is fine — tests do
  NOT read the real triple; `resolve()` is faked): swap-import instruction → output
  compiles; diff == stated lines exactly.
- Instruction whose target matches 2 lines ⇒ `DerivationError` (ambiguity is loud).
- Instruction producing an extra delta (bad replacement) ⇒ `DerivationError` before any
  output is returned.
- Output docstring contains the predecessor PATH and the stated diff.
- Gate: pytest (monotonic count) + ruff + mypy clean; stdlib only.
