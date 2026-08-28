# TICKET-071 — build_outer_freshness_fix generator (run-v4 meta-derivation)

**Status:** Open
**Cycle:** 16
**Build Order row:** Outer-freshness guard — run-v4 meta-derivation (16)

## Capability
`revolver/fixes.py`: `build_outer_freshness_fix(diagnosis, *, predecessor_runner: str)
-> list[NewFile]` — a deterministic generator that emits NEW `run-v4.py` content from
the run-v3.py predecessor text passed in READ-ONLY (never copied, never written to
~/Research/four).

The step-2 trajectory read becomes pass-freshness-guarded:
- snapshot the max trajectory sequence at pass start (`pass_start_max_seq`);
- after invoking the inner, the newest trajectory must be NEWER than the pass-start
  snapshot; if NO new sequence exists ⇒ the inner died unwitnessed (rc=124, empty
  output) ⇒ re-invoke the inner OR do the work yourself ⇒ the stale newest file is
  NEVER evidence of completion.

Every generated file carries a docstring stating diff-from-predecessor + evidence
citing trajectory_0027 (spoke-lint cycle 15) / trajectory_0029 (revolver cycle 14) and
run-v3.py:84 (the "READ its trajectory: the newest .json" defect line).

## Acceptance
- Generated run-v4 content contains the re-invoke / do-it-yourself branch and the
  pass-freshness guard; it does NOT reference the stale newest file as completion.
- Generated content is syntactically valid Python (validation.check_syntax ok).
- All paths under PROPOSAL_NAMESPACE (hard rule 7: additions only).
