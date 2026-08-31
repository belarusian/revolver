# TICKET-052 — tests for parse_trajectory_outcomes

Status: DONE
**Cycle:** 11 (Observe + report)
**Module:** `tests/test_observe.py`

## Capability
Extend `tests/test_observe.py` with a `TestParseTrajectoryOutcomes` class.

## Coverage
- single object (complete + non-complete), JSON array (file order preserved), no
  reorder/dedupe across restarts, malformed JSON -> empty, empty string -> empty,
  non-object/non-array payload -> empty, object without `outcome` key, custom
  `read_trajectory` seam (injects a fake; not consulted when text is present; empty
  seam -> empty), file order preserved.
- Use injectable seams / `patch.object` — never constructor-level patches; never touch
  the real filesystem.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
