# TICKET-029: Validation must be dry-run only (no I/O, no process)

Status: DONE

## Title
Validation must stay pure: in-memory compile/ast only.

## Evidence
- Deployment/relaunch is cycles 8-9; validation (cycles 6-7) must never write to
  disk or launch a process.
- `compile()`/`ast.parse()` are in-memory.

## Suggestion
Ensure `check_syntax`/`check_imports`/`validate_manifest_artifacts` use only
`compile()`/`ast.parse()` on the in-memory content string — no `Path.write_text`,
no `subprocess`, no `importlib` import of the generated module. Deterministic,
stdlib-only.

DONE — verified implemented in validation.py (tests in test_validation.py); closed out in Cycle 35.
