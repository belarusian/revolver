# TICKET-014: tests/test_proposal — round-trip + validation

Status: DONE
**Title:** Add `tests/test_proposal.py`: `propose()` round-trip for every failure_mode,
every new_file carries non-empty diff-from-predecessor + evidence, no existing path is
mutated, and `to_dict`/`from_dict` is lossless.

**Evidence:**
- `tests/test_diagnosis.py` establishes the house test style (class-per-concern, plain
  asserts, no fixtures) to mirror.
- The briefing requires: each failure_mode yields a valid `RepairProposal`; every
  new_file carries a non-empty diff-from-predecessor + evidence; no existing path is
  mutated; `to_dict`/`from_dict` lossless.
- `failure_mode == "none"` must yield an empty `new_files` list (no-op proposal).

**Impact:** The proposal core is unverified; a regression in the additive-only contract or
the round-trip would go undetected.

**Suggestion:**
- Parametrize over {"driver-death", "wall-kill", "stall-kill", "none"}: assert the
  proposal is valid, the failure_mode is preserved, and (for none) new_files is empty.
- For each actionable mode: assert every new_file has non-empty
  `diff_from_predecessor` and `evidence`, and its content embeds both docstring lines.
- Assert no new_file path collides with an existing repo path (hard rule 7).
- Assert `RepairProposal.from_dict(p.to_dict()) == p` (lossless round-trip).

DONE — verified implemented in proposal.py (tests in test_proposal.py); closed out in Cycle 36.
