# TICKET-025: No syntax validation of generated NEW-file content

## Title
`NewFile.content` emitted by the repair path is never checked to be valid Python.

## Evidence
- `revolver/fixes.py` builders emit `.py` plan files (e.g. `revolver/fixes/driver_death_relaunch.py`)
  whose content is a docstring + `NAME = value` lines. Nothing compiles that content.
- `revolver/manifest.py::build_manifest` composes the proposal but performs no
  syntax check on any `NewFile.content`.
- No `revolver/validation.py` exists on main.

## Impact
A generated `.py` plan file with a syntax error (unmatched quote, bad f-string)
would be reported as a valid manifest and only fail later, at deploy (cycles 8-9).

## Suggestion
Add `revolver/validation.py::check_syntax(content, *, path) -> SyntaxReport`
(`SyntaxReport(path, ok, error)`): compile in-memory with `compile()` (no disk
write); `.py` files must compile, non-Python files (e.g. `*.out` markers) are
reported ok with a "not python" note. Pure, deterministic.
