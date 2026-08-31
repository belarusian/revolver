# TICKET-013: hard rule 7 — never mutate an existing path

Status: DONE
**Title:** Enforce hard rule 7 across the proposal: a `RepairProposal` NEVER lists a
mutation of an existing path — only additions.

**Evidence:**
- The package docstring and the Cycle 3 briefing both state hard rule 7: "never mutate an
  existing file".
- `Diagnosis` carries the provenance (source, evidence) that motivates each addition; the
  rule is about the *shape* of the proposal (additions only), not its content.
- A stray later-cycle file can red the gate (Cycle 1 lesson) — the rule also keeps the
  generator from emitting edits that would collide with existing repo files.

**Impact:** Without an explicit check, a builder could silently emit a path that already
exists, violating the additive-only contract and breaking the "never mutate" guarantee.

**Suggestion:**
- `RepairProposal.validate(existing_paths=None)` raises `ValueError` if any
  `new_file.path` is in `existing_paths` (or, by default, if a path is not under a
  proposal-owned namespace such as `revolver/fixes/`).
- `propose()` calls `validate()` before returning so an invalid proposal never escapes.
- Tests assert no existing path is mutated for every failure mode.

DONE — verified implemented in proposal.py (tests in test_proposal.py); closed out in Cycle 36.
