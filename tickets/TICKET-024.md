# TICKET-024: tests/test_manifest.py

Status: DONE
Date: 2026-08-27
Cycle: 5 (synthesis)

## Title
No tests cover the ProposalManifest artifact.

## Evidence
- `tests/test_proposal.py`, `tests/test_launch_plan.py`, `tests/test_diagnosis.py`
  exist; no `tests/test_manifest.py`.

## Suggestion
Add `tests/test_manifest.py` covering:
- `build_manifest` over every failure_mode yields a valid manifest; healthy ->
  empty path + no-op plan.
- `validate()` passes for a good manifest and raises for a broken one (a
  proposal with an out-of-namespace path, or a plan with request_timeout <
  outer_wall).
- `render()` is deterministic and embeds each file path + the launch command.
- `to_dict`/`from_dict` lossless.

Acceptance:
- `pytest tests/test_manifest.py -q` green; full suite green.

DONE — verified implemented in manifest.py (tests in test_manifest.py); closed out in Cycle 35.
