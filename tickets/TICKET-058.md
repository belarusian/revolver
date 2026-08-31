# TICKET-058 — render(report) -> str (deterministic human-readable final report)

Status: DONE
## Capability
`render(report: FinalReport) -> str`.

## Spec
- A deterministic, human-readable text report answering "did the diagnosed failure mode recur in the observed run?".
- Sections: pipeline/failure_mode, done/in-flight/gaps (marker observation), trajectory outcomes, merge-commit status (merged/missing), and the RECURRED/clean verdict.
- Pure, deterministic, stdlib-only; READ-ONLY. Stable across a to_dict/from_dict round-trip.

## Acceptance
- render deterministic + embeds each section + stable across round-trip.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
