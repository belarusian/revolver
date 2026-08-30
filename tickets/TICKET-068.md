# TICKET-068 — additive Diagnosis extension (client-timeout + inner-wall modes)

**Status:** DONE
**Cycle:** 14 (Fix-class templates + replay acceptance, cycles 14-15)

## Capability
Extend `revolver/diagnosis.py` (additive only) so the two founding failure modes are
addressable:
- a **client-timeout** mode (the cancel-loop: evidence of client-side request cancels on
  long inferences), and
- an **inner-wall** mode (wall-kill AFTER merge on a heavy cycle — distinguished from
  wall-kill-no-merge by the PRESENCE of the merge).

`_derive_failure_mode` is extended to return the new modes; `to_dict`/`from_dict`
round-trip the new fields. Existing fields/modes stay byte-compatible.

## Invariants
- Additive only: existing fields and the four existing failure modes are unchanged;
  old dicts (without the new fields) still load via `from_dict` (it filters to known
  fields).
- `to_dict`/`from_dict` round-trip the new fields losslessly.
- The new modes are distinguishable from the existing wall-kill mode: inner-wall
  requires the merge to be present (the merge is on main), so it is NOT
  wall-kill-no-merge.
