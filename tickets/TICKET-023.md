# TICKET-023: Lossless to_dict / from_dict for ProposalManifest

Status: DONE
Date: 2026-08-27
Cycle: 5 (synthesis)

## Title
ProposalManifest has no serialization contract. The repo already establishes a
lossless `to_dict`/`from_dict` idiom on Diagnosis, RepairProposal, and
LaunchPlan; nothing applies it to the manifest.

## Evidence
- `Diagnosis.to_dict`/`from_dict`, `RepairProposal.to_dict`/`from_dict`,
  `LaunchPlan.to_dict`/`from_dict` all exist and round-trip losslessly.
- No `to_dict`/`from_dict` on a manifest type.

## Suggestion
Add `ProposalManifest.to_dict() -> dict` (lossless; nest diagnosis, proposal,
launch_plan via their own round-trips) and
`ProposalManifest.from_dict(d) -> ProposalManifest` (the inverse).

Acceptance:
- `ProposalManifest.from_dict(m.to_dict()) == m` for any valid manifest.
- `to_dict`/`from_dict` are exact inverses (no field dropped).

DONE — verified implemented in manifest.py (tests in test_manifest.py); closed out in Cycle 35.
