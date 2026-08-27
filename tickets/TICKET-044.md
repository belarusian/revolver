# TICKET-044: relaunch module invariants — no process kill, append-not-truncate

Status: OPEN
Date: 2026-08-27
Cycle: 9 synthesis audit
Target: `revolver/relaunch.py` (NEW module) — cross-cutting invariants.

## Title
Enforce the cross-cutting invariants across the relaunch module: NO process kill
(kill stays sentry's, JUNIOR.md §8) and append-not-truncate (JUNIOR.md §8).

## Evidence
- JUNIOR.md §8: "kill the INNER pid only; the outer re-invokes (2-phase). Never
  kill the driver." The relaunch module must contain no kill/terminate logic.
- JUNIOR.md §7 scar: "Continuation launch reused a filename with `>` -> truncated
  prior cycle markers." The resume command must append (`>>`) to cycles.out, never
  truncate.
- The marker line is the one build_launch_plan already produced and check_launch_plan
  already validated (Cycle 7); relaunch does not re-derive it.

## Suggestion
- No `os.kill` / `signal` / `subprocess`-kill logic anywhere in relaunch.py.
- The resume command uses `>>` (append) to cycles.out, never a lone `>`.
- verify_relaunch is read-only (reads cycles.out, probes the driver); it never
  terminates a process.
- Pure, deterministic, stdlib-only; overridable seams for all I/O.
