# TICKET-096: Malformed Sphinx refs in `build_inner_wall_fix` docstring (`:func::` / `:class:`)

Status: OPEN
Cycle: 37 (synthesis audit)

## Purpose
`build_inner_wall_fix`'s docstring contains broken Sphinx cross-reference roles that
render as literal text and break any Sphinx/`autodoc` build. The builder is one of the
three fix-class builders this audit verifies, so its docstring should be clean.

## Evidence
`revolver/fixes.py:357` (inside the `build_inner_wall_fix` docstring, lines 353-374):

    This builder is a THIN INSTRUCTION EMITTER over
    :func:: it composes a single :class:
    (replace the --inner-seconds value) and hands the predecessor PATH to

- `:func::` is a malformed role — a `:func:` with no target followed by a stray `:`.
- `:class:` is a role with no target (empty), so it renders as a literal `:class:`.
- The intended sentence is "a THIN INSTRUCTION EMITTER over ``revolver.derive``: it
  composes a single ``ChangeInstruction`` (replace the --inner-seconds value) and
  hands the predecessor PATH to ``derive()``". The two named symbols
  (`revolver.derive` / `ChangeInstruction`) were dropped and replaced by the broken
  roles.
- `grep -n ":func::\|:class::\|:func:\|:class:" revolver/fixes.py` returns only
  `revolver/fixes.py:357` — this is the only malformed role in the module.

## Impact
- Sphinx `autodoc` / `napoleon` builds emit warnings and render the literal
  `:func::` / `:class:` text in the generated API docs.
- The docstring no longer names the two symbols it actually uses
  (`revolver.derive`, `ChangeInstruction`), so a reader cannot tell which
  `derive()` is meant without reading the body.

## Suggestion
Rewrite lines 356-360 to name the symbols explicitly, e.g.:

    This builder is a THIN INSTRUCTION EMITTER over ``revolver.derive``: it
    composes a single ``ChangeInstruction`` (replace the --inner-seconds value)
    and hands the predecessor PATH to ``derive()``, which reads the file
    read-only, applies the edit, and verifies by construction
    (compile + diff == stated lines).

No behavior change. Re-run `ruff check revolver/` (docstring-only edit) and
`pytest tests/test_fixes_generators.py -q` (unchanged).
