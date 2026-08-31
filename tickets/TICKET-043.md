# TICKET-043: tests/test_relaunch.py — coverage for the relaunch module

Status: DONE
Date: 2026-08-27
Cycle: 9 synthesis audit
Target: `tests/test_relaunch.py` (NEW) — tests for revolver/relaunch.py.

## Title
Add tests for first_not_done_cycle, plan_relaunch, and verify_relaunch using
injectable seams / patch.object — never spawn a real process or touch the real
filesystem.

## Evidence
- Briefing acceptance criteria:
  * first_not_done_cycle: first gap, all-done -> None, empty -> None, out-of-order
    input, custom `done` seam.
  * plan_relaunch: resume from first not-done, all-done -> no-op plan, command
    scoped to resume_from..last, no-op note.
  * verify_relaunch: marker present + driver alive -> ok; marker missing -> not ok;
    driver dead -> not ok; no-op plan -> ok + note, probes nothing.
- Rule 4: use patch.object(instance, 'method'), not constructor-level patches.
- Cycle 8 test_deploy.py is the reference for seam-injection style (MagicMock
  seams, no real subprocess / filesystem).

## Suggestion
`tests/test_relaunch.py` covering every acceptance criterion above. Injectable
seams / patch.object; never spawn a real process or touch the real filesystem.

DONE — verified implemented in relaunch.py (tests in test_relaunch.py); closed out in Cycle 35.
