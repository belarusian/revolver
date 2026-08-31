# TICKET-042: verify_relaunch() + RelaunchVerification — relaunch verification

Status: DONE
Date: 2026-08-27
Cycle: 9 synthesis audit
Target: `revolver/relaunch.py` (NEW module) — relaunch verification.

## Title
Add `RelaunchVerification` dataclass (ok, marker_appended, driver_alive, errors,
note) and `verify_relaunch(manifest, *, read_cycles_out=None, driver_alive=None) ->
RelaunchVerification`: verify the relaunch actually took effect.

## Evidence
- JUNIOR.md §8 "Done" = `========== CYCLE N done ==========` in cycles.out AND no
  run-cycles process. Verification reads cycles.out (marker present) and probes the
  driver (alive).
- JUNIOR.md §8: "Never kill the driver." Verification is read-only — it reads
  cycles.out and probes the driver; it NEVER kills a process (kill stays sentry's).
- `manifest.launch_plan.cycles_out_append` is the marker line to look for in
  cycles.out (produced by build_launch_plan, validated by check_launch_plan, Cycle 7).
- Overridable seams keep it pure + testable: `read_cycles_out` (default: real file
  read) and `driver_alive` (default: a real process probe).

## Suggestion
`verify_relaunch(manifest, *, read_cycles_out=None, driver_alive=None) ->
RelaunchVerification`:
- No-op plan (empty command) -> ok=True, note "all done / no-op", probes nothing.
- Else: `marker_appended` = the marker line is present in cycles.out (via
  read_cycles_out seam); `driver_alive` = the driver process is alive (via
  driver_alive seam). `ok = marker_appended and driver_alive`.
- Errors list names the failed check(s). NO process kill.
- Pure logic; the only I/O is through the seams.

DONE — verified implemented in relaunch.py (tests in test_relaunch.py); closed out in Cycle 35.
