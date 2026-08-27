# TICKET-039: tests/test_deploy.py — deploy + relaunch coverage

Status: OPEN
Date: 2026-08-27
Cycle: 8 synthesis audit
Target: test coverage for revolver/deploy.py.

## Evidence
- The Build Order requires every module to have tests before merge (work strategy).
  Cycles 1-7 each landed a `tests/test_<module>.py`. There is no
  `tests/test_deploy.py` on main.
- Rule 4: use `patch.object(instance, "method")` / injectable seams — never
  constructor-level patches; never spawn a real process in tests.

## Suggestion
Add `tests/test_deploy.py` covering: `deploy_manifest` writes every NEW file under
`base_dir` (additions-only) when approved; does NOT overwrite an existing path (hard
rule 7); a not-approved manifest writes nothing and reports a "not approved" note; a
healthy (no-op) manifest writes nothing. `relaunch` runs the launch command for an
actionable plan (via the seam); a no-op plan launches nothing and reports a "no-op"
note. Use injectable seams / `patch.object` — never spawn a real process.
