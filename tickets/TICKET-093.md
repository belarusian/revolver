# TICKET-093: Close-out verification — founding modules (TICKET-001..014)

Status: DONE
Cycle: 36 (synthesis audit)
Parent: TICKET-001, TICKET-002, TICKET-003, TICKET-004, TICKET-005, TICKET-006, TICKET-007, TICKET-008, TICKET-009, TICKET-010, TICKET-011, TICKET-012, TICKET-013, TICKET-014

## Purpose
Close-out verification for the stale backlog tickets TICKET-001..014 (founding
modules, cycles 1-4). Confirms each ticket's named symbol exists in its module
and that the module's test module passes, so the tickets can be flipped to DONE.
These tickets never carried a `Status:` line (inconsistent format), so the flip
is an insert-after-H1, not an OPEN -> DONE substitution.

## Evidence (symbol presence)
- TICKET-001 `Diagnosis` dataclass: `revolver/diagnosis.py:52`.
- TICKET-002 `parse_raw_artifacts(...)`: `revolver/diagnosis.py:326` (pure, no I/O).
- TICKET-003 round-trip + validate: `Diagnosis.to_dict` :157 / `from_dict` :191 /
  `validate` :199; tests `test_round_trip` :206, `test_validate_accepts_valid` :230
  in `tests/test_diagnosis.py`.
- TICKET-004 `SentryPin` + pin: `revolver/sentry_pin.py:30` (`parse_requirement` :66,
  `render_requirement` :79, `validate_pin` :91) + the `[project.optional-dependencies]`
  `sentry = ["sentry @ git+...@9713735..."]` pin in `pyproject.toml:13`.
- TICKET-005 diagnosis + sentry_pin round-trip: `Diagnosis.to_dict`/`from_dict`
  round-trip (`tests/test_diagnosis.py:206`) + `SentryPin` parse/render round-trip
  (`tests/test_diagnosis.py:350`, `:425`).
- TICKET-006 `SentryClient`: `revolver/sentry_client.py:36`.
- TICKET-007 `run_check` seam: `revolver/sentry_client.py:46` (returns
  `(stdout, exit_code)`; tests override on the instance, nothing shells out).
- TICKET-009 `diagnose_via_sentry` runner: `revolver/sentry_client.py` (composes
  `SentryClient.run_check` + `parse_raw_artifacts`).
- TICKET-010 `NewFile`: `revolver/proposal.py:35`.
- TICKET-011 `RepairProposal`: `revolver/proposal.py:72`.
- TICKET-012 `propose(diagnosis, *, builders=None)`: `revolver/proposal.py:136`
  (injectable builder registry; healthy -> empty path).
- TICKET-013 per-mode builders: `revolver/fixes.py` `build_driver_death_fix` :75,
  `build_wall_kill_fix` :118, `build_stall_kill_fix` :161, `build_none_fix` :205.
- TICKET-014 hard-rule-7 no-mutate: every generated file header carries
  "additions only; hard rule 7: never mutate" (`revolver/fixes.py:48`, `:65`,
  `:226`, `:486`); builders return NEW `NewFile`s, never mutate existing files.

## Test evidence
- `pytest tests/test_diagnosis.py -q` -> 47 passed.
- `pytest tests/test_sentry_client.py -q` -> 7 passed.
- `pytest tests/test_proposal.py -q` -> 30 passed.
- `pytest tests/test_fixes_generators.py -q` -> 22 passed.

## Verdict
All fourteen tickets' named symbols exist and the test modules are green. Flip
TICKET-001..014 to DONE (insert `Status: DONE` after the H1; these tickets have no
prior `Status:` line).
