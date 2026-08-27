# TICKET-026: No import validation of generated NEW-file content

## Title
`NewFile.content` imports are never checked against the known revolver namespace.

## Evidence
- `revolver/fixes.py` plan files may carry `import`/`from ... import` statements.
- No `ImportReport`/`check_imports` exists on main.

## Impact
A generated file importing an unknown module would pass the manifest and fail at
runtime with ModuleNotFoundError.

## Suggestion
Add `revolver/validation.py::check_imports(content, *, known_modules=None) ->
ImportReport` (`ImportReport(path, ok, missing)`): parse import statements via
`ast`, report any top-level module that is neither stdlib nor in `known_modules`
(default: the revolver package modules). Static name check — does NOT require the
module to be importable at runtime. Pure, deterministic.
