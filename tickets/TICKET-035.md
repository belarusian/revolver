# TICKET-035: DeployReport + deploy_manifest (additions-only, on human approval)

Status: DONE
Date: 2026-08-27
Cycle: 8 synthesis audit
Target: deploy the validated NEW path on human approval (revolver/deploy.py).

## Evidence
- `revolver/manifest.py::ProposalManifest.proposal.new_files` is the list of `NewFile`
  (path/content/diff/evidence) to deploy; `revolver/proposal.py::PROPOSAL_NAMESPACE`
  ("revolver/fixes/") is the additions-only namespace (hard rule 7).
- `revolver/proposal.py::RepairProposal.validate(existing_paths)` already rejects a
  `new_file.path` that collides with an existing path — the deploy-time no-clobber rule
  mirrors this at write time.
- The Build Order (cycle log) names cycles 8-9 "Deploy + relaunch ... on human approval".
  There is no `revolver/deploy.py` on main.

## Suggestion
Add `revolver/deploy.py` with a `DeployReport` dataclass (ok, deployed_paths, errors,
note) and `deploy_manifest(manifest, *, base_dir, write_file=None, approved=None) ->
DeployReport`: on human approval, write every `NewFile` in `manifest.proposal.new_files`
to `base_dir/<path>` (additions-only — never overwrite an existing path; hard rule 7).
`write_file` is an overridable seam (default: real `open(..., "w")`); `approved` is an
overridable seam (default: a human-approval callable that returns False). A not-approved
manifest is reported ok with a "not approved" note and writes nothing. Pure logic; the
only I/O is through the `write_file` seam.

DONE — verified implemented in deploy.py (tests in test_deploy.py); closed out in Cycle 35.
