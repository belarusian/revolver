# TICKET-103: `README.md` `fixes.py` module row lists 4 of 7 builders and misstates the marker-file rule

Status: DONE
Cycle: 53 (synthesis audit — steady-state maintenance verification)
Parent: TICKET-087, TICKET-090, TICKET-100

## Evidence

`README.md:79` (before fix):

    | `fixes.py` | Concrete per-failure-mode fix builders (`build_driver_death_fix`, `build_wall_kill_fix`, `build_stall_kill_fix`, `build_none_fix`) + the `FIX_BUILDERS` registry. Each actionable builder emits a plan file PLUS a `cycles.out` marker file; the healthy builder emits an empty path. |

Two problems, both contradicted by `revolver/fixes.py`:

1. **Builder list is stale.** The row names only 4 builders. The code defines 7
   (line numbers from `grep -n "def build_" revolver/fixes.py`):
   `build_driver_death_fix` (:75), `build_wall_kill_fix` (:118),
   `build_stall_kill_fix` (:161), `build_none_fix` (:205),
   `build_client_timeout_fix` (:259), `build_inner_wall_fix` (:348),
   `build_outer_freshness_fix` (:475). The `FIX_BUILDERS` registry
   (`revolver/fixes.py:580-586`) registers 6 of the 7 (all except
   `build_outer_freshness_fix`, which is called directly). The sibling catalog
   `docs/MODULES.md:6` already lists all 7 correctly — the README row is the
   outlier.

2. **The "plan file PLUS marker file" claim is wrong for the derive-based
   builders.** Only the three original builders emit a plan file plus a
   `cycles.out` marker file (2 NewFiles each: `revolver/fixes.py:103-110`,
   `:146-153`, `:190-197`). The three derive-by-reference builders emit derived
   NEW-file variants with NO marker file: `build_client_timeout_fix` returns 4
   derived variants (`revolver/fixes.py:338-346`), `build_inner_wall_fix`
   returns 1 (`:420-427`), `build_outer_freshness_fix` returns 2 (`:562-570`).
   `build_none_fix` returns an empty list (`:205-258`).

## Impact
- The root README is the first thing a newcomer reads; its `fixes.py` row
  understates the module's surface (4 of 7 builders) and states a per-builder
  emission rule ("each actionable builder emits a plan file PLUS a marker file")
  that is false for 3 of the 6 actionable builders. A reader would expect a
  marker file from the client-timeout / inner-wall / outer-freshness repair
  paths and find none.
- Inconsistent with `docs/MODULES.md:6`, which is correct.

## Suggestion
Rewrite the `README.md:79` row to (a) list all 7 builders and (b) state the
emission rule accurately: the three original builders (driver-death, wall-kill,
stall-kill) each emit a plan file PLUS a `cycles.out` marker file; the three
derive-by-reference builders (client-timeout, inner-wall, outer-freshness) emit
derived NEW-file variants; the healthy builder emits an empty path. Docs-only
change; no test impact.

## Resolution (Cycle 53)
Rewrote `README.md:79` to list all 7 builders and to state the emission rule
accurately (three original builders emit plan + marker; three derive-by-reference
builders emit derived variants; healthy builder emits empty). Verified the builder
counts against `revolver/fixes.py` (2/2/2 NewFiles for the original three; 4/1/2
for the derive-based three; 0 for none) and the registry at `:580-586`.
Docs-only change; gate re-measured green (415 passed / ruff clean / mypy clean,
14 files).
