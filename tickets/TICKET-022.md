# TICKET-022: Deterministic render() to a human-readable text report

Status: DONE
Date: 2026-08-27
Cycle: 5 (synthesis)

## Title
No `render()` on ProposalManifest produces a stable, human-readable text report
of the diagnosis, the NEW-file-only repair path, and the derived launch plan.

## Evidence
- The seed renders to machine formats (report.json, projects.tsv) and an ad-hoc
  non-deterministic dry-run print; never a deterministic human-readable text
  report of a proposal.
- `revolver/` has no `render`/`to_text` method on any type.

## Suggestion
Add `ProposalManifest.render() -> str`: deterministic, human-readable text
report (pipeline, failure_mode, verdict, each NEW file path + its
diff/evidence, the launch command + marker + budgets). Pure string build — no
I/O. Fixed section order; files in stored (builder) order.

Acceptance:
- `m.render()` is byte-identical across two calls (deterministic; no clock, no
  randomness, no dict-iteration-order dependence).
- Output embeds each NEW file path and the launch command.
- Re-rendering after a to_dict/from_dict round-trip yields identical text.

DONE — verified implemented in manifest.py (tests in test_manifest.py); closed out in Cycle 35.
