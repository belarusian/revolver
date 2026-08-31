# TICKET-002: revolver.diagnosis — raw-artifact fallback when sentry is not installed

Status: DONE
**Title:** Degrade to raw-artifact parsing (cycles.out markers, gate log cycle blocks, newest trajectory outcome) and say so.

**Evidence:** The mission states "when not importable, revolver degrades to
raw-artifact parsing and says so." cycles.out carries `========== CYCLE N ... ==========`
start and `========== CYCLE N done ==========` markers; the gate log carries
`## Cycle N` headings; trajectories carry an `outcome` field.

**Impact:** If sentry is not installed (the default for a fresh clone), `diagnose()`
must still produce a usable `Diagnosis` and must record `source="raw-artifacts"`.

**Suggestion:** Add `parse_raw_artifacts(cycles_out_text, gate_log_text, trajectory_outcome)`
and a high-level `diagnose(project_dir, *, read_file=None, sentry_available=None)`
with an overridable I/O seam (the sentry pattern).

DONE — verified implemented in diagnosis.py (tests in test_diagnosis.py); closed out in Cycle 36.
