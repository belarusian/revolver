# TICKET-021: Whole-manifest validate() re-checking every invariant

Status: DONE
Date: 2026-08-27
Cycle: 5 (synthesis)

## Title
No single `validate()` on ProposalManifest re-checks the proposal's
additions-only contract AND the launch plan's invariants together. A manifest
that passes `validate()` must be guaranteed additions-only AND launch-safe.

## Evidence
- `RepairProposal.validate(existing_paths)` enforces hard rule 7 (namespace +
  no existing-path mutation).
- `LaunchPlan.validate()` enforces request_timeout >= outer_wall, one pipeline
  per endpoint, non-negative budgets, non-empty pipeline_id/version.
- No composite check ties them together.

## Suggestion
Add `ProposalManifest.validate(existing_paths=None) -> ProposalManifest`:
- call `self.proposal.validate(existing_paths)` (hard rule 7);
- call `self.launch_plan.validate()` (launch invariants);
- raise ValueError naming the FIRST violation.

Acceptance:
- A good manifest passes `validate()`.
- A proposal with an out-of-namespace path -> ValueError (hard rule 7).
- A plan with request_timeout < outer_wall -> ValueError.
- A plan with one_pipeline_per_endpoint False -> ValueError.

DONE — verified implemented in manifest.py (tests in test_manifest.py); closed out in Cycle 35.
