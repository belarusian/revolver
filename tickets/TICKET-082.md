# TICKET-082 — Package version 0.1.0 does not match tag v0.2.0

**Status: OPEN**
**Source: Cycle 28 synthesis audit — toolchain-pin verification**

## Evidence
- `pyproject.toml` line 7: `version = "0.1.0"`
- `revolver/__init__.py` line 9: `__version__ = "0.1.0"`
- `README.md` line 109: `0.1.0 - the 12-cycle build ... is complete`
- `git tag -v v0.2.0`: tag message reads "v0.2.0 — Build Order complete (cycles 1-24)"
- `git merge-base --is-ancestor v0.2.0 main` → true (tag at commit 183a08e)
- 4 commits exist on main after v0.2.0 (cycles 25-28: ruff E731 fix, toolchain pin)

## Impact
`pip install revolver` reports version 0.1.0. Any downstream consumer checking
`revolver.__version__` or `importlib.metadata.version("revolver")` sees 0.1.0,
not 0.2.0. The tag and the package disagree. This breaks version-based
dependency resolution and audit trails.

## Suggestion
Bump `pyproject.toml` to `version = "0.2.0"`, bump `revolver/__init__.py` to
`__version__ = "0.2.0"`, update README version section. Commit as a chore.
No new tag needed — v0.2.0 already exists and is on main.
