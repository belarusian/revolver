# TICKET-011: revolver.proposal — propose(diagnosis) dispatcher

**Title:** Add `propose(diagnosis) -> RepairProposal` that maps a `Diagnosis.failure_mode`
to the matching fix builder and assembles a minimal NEW-file-only repair path.

**Evidence:**
- `Diagnosis.failure_mode` is one of {"driver-death", "wall-kill", "stall-kill", "none"}
  (see `diagnosis.py::_derive_failure_mode`).
- `failure_mode == "none"` (healthy) must yield an empty `new_files` list (no-op
  proposal) — the generator is additive and must not invent work for a healthy pipeline.
- The generator must be pure: no disk writes, no process launch (deployment/relaunch is
  cycles 8-9; validation is cycles 6-7).

**Impact:** Without `propose()` there is no entry point turning a diagnosis into a
proposal; the fix builders (TICKET-012) have no dispatcher.

**Suggestion:**
- `propose(diagnosis, *, builders=None) -> RepairProposal`: a registry mapping each
  failure_mode to a fix-builder callable; `builders` is an overridable seam (the
  sentry pattern) so tests can inject fakes.
- Unknown/healthy failure_mode -> empty `new_files`, rationale states "no action needed".
- Deterministic: same diagnosis -> same proposal (no timestamps, no randomness).
