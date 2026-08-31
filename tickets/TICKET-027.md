# TICKET-027: No whole-manifest artifact validation

Status: DONE

## Title
`ProposalManifest` has no dry-run validation over its generated NEW files.

## Evidence
- `revolver/manifest.py::validate()` checks hard rule 7 + launch invariants but
  never inspects the *content* of the `NewFile`s.
- No `validate_manifest_artifacts` exists on main.

## Impact
A manifest whose generated files are syntactically broken or import unknown
modules is still "valid" — the breakage is only caught at deploy.

## Suggestion
Add `revolver/validation.py::validate_manifest_artifacts(manifest, *,
known_modules=None) -> list[ValidationResult]`: run syntax + import checks over
every `NewFile` in `manifest.proposal.new_files`; return one `ValidationResult`
per file (path, syntax_ok, imports_ok, errors). No I/O, no process launch.

DONE — verified implemented in validation.py (tests in test_validation.py); closed out in Cycle 35.
