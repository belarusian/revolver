# TICKET-033: tests for check_launch_plan — every acceptance criterion

## Title
`tests/test_validation.py` must cover `check_launch_plan` for every briefing criterion.

## Evidence
- Briefing: accept a healthy no-op plan (no-op note) and an actionable plan (nohup +
  append marker + verbatim pin + request_timeout >= outer_wall + one pipeline per
  endpoint); reject a command without nohup; reject a marker that is not an append
  (empty or truncate form); reject a pin that differs from the expected pin; reject
  request_timeout < outer_wall; reject one_pipeline_per_endpoint False.

## Suggestion
Parametrized tests: (a) no-op plan -> ok + no-op note; (b) healthy actionable plan -> ok;
(c) command without nohup -> not ok; (d) empty marker -> not ok; (e) truncate marker
(`> cycles.out`) -> not ok; (f) pin differs from expected -> not ok; (g)
request_timeout < outer_wall -> not ok; (h) one_pipeline_per_endpoint False -> not ok;
(i) request_timeout == outer_wall -> ok (equality allowed); (j) self-consistency pin
(no expected) -> ok. Deterministic.
