# TICKET-020: ProposalManifest data model + build_manifest()

Status: OPEN
Date: 2026-08-27
Cycle: 5 (synthesis)

## Title
No single artifact unifies the Diagnosis, the NEW-file-only RepairProposal, and
the derived dry-run LaunchPlan. They are three disconnected types with no shared
version stamp and no single place to reason about them together.

## Evidence
- `revolver/proposal.py` defines `RepairProposal` (pipeline_id, diagnosis,
  new_files, rationale, version) and `propose(diagnosis)`.
- `revolver/launch_plan.py` defines `LaunchPlan` and
  `build_launch_plan(proposal)`.
- `revolver/diagnosis.py` defines `Diagnosis`.
- Nothing composes the three into one versioned, serializable artifact.

## Suggestion
Add `revolver/manifest.py` with:
- `MANIFEST_VERSION = "1.0"`.
- `ProposalManifest` dataclass: `pipeline_id`, `diagnosis: Diagnosis`,
  `proposal: RepairProposal`, `launch_plan: LaunchPlan`, `version: str`.
- `build_manifest(diagnosis, *, builders=None) -> ProposalManifest`: compose
  `propose(diagnosis, builders=builders)` + `build_launch_plan(proposal)` into
  one artifact. Healthy diagnosis -> manifest with empty repair path + no-op
  launch plan. Pure, deterministic (same Diagnosis -> same manifest).

Acceptance:
- `build_manifest(d)` returns a `ProposalManifest` whose `.proposal` ==
  `propose(d)` and `.launch_plan` == `build_launch_plan(propose(d))`.
- Healthy (failure_mode=="none") -> empty `new_files` + no-op plan.
- Deterministic: `build_manifest(d).to_dict() == build_manifest(d).to_dict()`.
