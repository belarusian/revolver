# TICKET-036: deploy_manifest must never overwrite an existing path (hard rule 7)

Status: DONE
Date: 2026-08-27
Cycle: 8 synthesis audit
Target: additions-only deploy (revolver/deploy.py).

## Evidence
- `revolver/proposal.py::RepairProposal.validate()` raises ValueError when a
  `new_file.path` is in `existing_paths` ("hard rule 7 violated ... already exists
  (mutation)"). The deploy step must enforce the same rule at write time, not just rely
  on the proposal having been validated earlier.
- JUNIOR.md §7 scar: a `>` on an existing filename wiped prior markers. Clobbering an
  existing path at deploy time is the same class of data-loss scar.

## Suggestion
`deploy_manifest` must check, for each `NewFile`, whether `base_dir/<path>` already
exists (via an overridable `path_exists` seam, default `os.path.exists`). If it exists,
append an error to the report (do NOT clobber) and skip the write. A manifest whose
target path already exists is reported not-ok with the collision error. This mirrors
`RepairProposal.validate()`'s no-collision rule at deploy time.

DONE — verified implemented in deploy.py (tests in test_deploy.py); closed out in Cycle 35.
