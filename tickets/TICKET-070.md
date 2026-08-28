# TICKET-070 — Diagnosis intake fields for the outer-freshness class

**Status:** DONE
**Cycle:** 16
**Build Order row:** Outer-freshness guard — run-v4 meta-derivation (16)

## Capability
Additive intake fields to `revolver/diagnosis.py` for the UNWITNESSED INNER DEATH /
stale-trajectory-slot failure class:
- `no_new_trajectory_witnessed: bool` (default False) — True when the inner pass died
  (rc=124, EMPTY output) and NO trajectory newer than the pass-start snapshot exists.
- `pass_start_max_seq: int | None` (default None) — the max trajectory sequence number
  present at the START of the pass (the freshness baseline).

Wire a new `failure_mode` value `"outer-freshness"` through `_derive_failure_mode()`
(additive: checked after the founding modes, before the plain wall-kill) and through
`to_dict()` / `from_dict()` (lossless round-trip). Existing modes stay byte-compatible.

## Acceptance
- `Diagnosis(no_new_trajectory_witnessed=True, pass_start_max_seq=26)` derives
  `failure_mode == "outer-freshness"` via `_derive_failure_mode`.
- Round-trip `to_dict`/`from_dict` preserves both fields.
- A diagnosis without the new fields derives exactly as before (no regression).
