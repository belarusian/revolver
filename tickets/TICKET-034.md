# TICKET-034: tests for validate_manifest_launch — every failure_mode ok, broken plan fails

Status: DONE

## Title
`tests/test_validation.py` must cover `validate_manifest_launch`.

## Evidence
- Briefing: `validate_manifest_launch` over every failure_mode yields an ok report; a
  manifest with a broken launch plan yields a failing report.

## Suggestion
Loop over all four failure_modes (driver-death, wall-kill, stall-kill, none) building a
manifest via `build_manifest` and assert `validate_manifest_launch(m).ok` is True. Then
build a manifest whose launch_plan is broken (e.g. request_timeout < outer_wall, or
command without nohup) and assert the report is not ok with a descriptive error.

DONE — verified implemented in validation.py (tests in test_validation.py); closed out in Cycle 35.
