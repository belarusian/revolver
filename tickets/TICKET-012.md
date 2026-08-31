# TICKET-012: revolver.fixes — per-failure-mode fix builders

Status: DONE
**Title:** Add `revolver/fixes.py` with pure, deterministic, stdlib-only fix builders for
each failure mode (driver-death, wall-kill, stall-kill, none) that emit NEW-file content.

**Evidence:**
- `sentry/cli.py` defines the three actionable failure modes: driver-death (driver
  process dead), wall-kill-no-merge (cycle wall-killed without merging), stall (inner PID
  hung — kill the inner PID only, NEVER the driver).
- Each generated file's content must embed a docstring: "Diff from predecessor: ..." +
  "Evidence: ..." (house convention already used in `diagnosis.py`/`sentry_client.py`).
- The builders must be pure functions of the `Diagnosis` — no I/O, no clock, no
  randomness — so the proposal is reproducible.

**Impact:** The proposal core (TICKET-010/011) has no concrete content to emit; the
repair path would be empty for every actionable failure mode.

**Suggestion:**
- `build_driver_death_fix(diagnosis) -> list[NewFile]`, `build_wall_kill_fix(diagnosis)`,
  `build_stall_kill_fix(diagnosis)`, `build_none_fix(diagnosis) -> []`.
- Each builder returns NEW-file-only `NewFile`s whose `content` docstring states the
  diff-from-predecessor and the motivating evidence (the diagnosis fields).
- `FIX_BUILDERS: dict[str, Callable[[Diagnosis], list[NewFile]]]` registry keyed by
  failure_mode, defaulting unknown modes to the none-builder.

DONE — verified implemented in fixes.py (tests in test_fixes_generators.py); closed out in Cycle 36.
