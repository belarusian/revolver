# TICKET-085 — No docs/ directory; README is the sole documentation

**Status: DONE**
**Source: Cycle 28 synthesis audit — toolchain-pin verification**

## Evidence
- `ls docs/` → `NO_DOCS_DIR`
- The only documentation is `README.md` (8265 bytes, single file).
- No `docs/MODULES.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, or
  `docs/README.md` exists.
- The README serves as both newcomer guide and module catalog, but it is
  already stale (see TICKET-083) and conflates architecture, API, and
  onboarding in one file.
- 14 modules, 14 test files, 81 tickets — the project has outgrown a single
  README.

## Impact
- No machine-readable module catalog for tooling (e.g., an auditor script
  cannot cross-reference modules against docs).
- No API reference separate from the narrative README.
- No architecture document explaining the closed-loop design in isolation
  from the quickstart.
- Newcomers must read the full README to find any single fact.

## Suggestion
Create `docs/` with:
- `docs/MODULES.md` — catalog of all 14 modules with one-line descriptions
  and dependency edges.
- `docs/API.md` — public function signatures with type hints.
- `docs/ARCHITECTURE.md` — the closed-loop design (diagnose → propose →
  approve → deploy → observe) with the seam pattern.
- `docs/README.md` — newcomer landing page pointing to the above.
This is a documentation-only change; no code changes.
