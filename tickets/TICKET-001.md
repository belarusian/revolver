# TICKET-001: revolver.diagnosis — parse sentry check report into a typed Diagnosis

Status: DONE
**Title:** Parse the sentry check/rescue report (stable 8-line dialect) into a structured, versioned `Diagnosis` record.

**Evidence:** `sentry/cli.py::_format_check_report` emits a fixed, ordered dialect:
`driver: alive|dead`, `driver-death: DETECTED cycle N|none`,
`wall-kill-no-merge: DETECTED cycle N|none`, `stall: <action> (<reason>)`,
`live work: yes (root=PID) [:: samples]|no`,
`cycles: started=[..] done=[..] in_flight=[..] wall_kill=[..]`,
`gate-blocks: [..]`, `verdict: ACTION NEEDED|HEALTHY`.
`revolver/diagnosis.py` does not exist on main (only a partial branch `cycle-1-diagnosis`).

**Impact:** Without a typed `Diagnosis`, revolver cannot consume a sentry diagnosis
deterministically; downstream fix-class selection (cycles 3-5) has no structured input.

**Suggestion:** Add `revolver/diagnosis.py` with a `Diagnosis` dataclass (pipeline id,
failure mode, evidence, endpoint pin, source provenance, raw) and a pure
`parse_sentry_report(text) -> Diagnosis`. Deterministic, stdlib-only, no I/O.

DONE — verified implemented in diagnosis.py (tests in test_diagnosis.py); closed out in Cycle 36.
