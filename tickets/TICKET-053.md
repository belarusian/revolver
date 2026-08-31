# TICKET-053 — tests for report (recurrence verdict)

Status: DONE
**Cycle:** 11 (Observe + report)
**Module:** `tests/test_observe.py`

## Coverage
- clean run -> recurred False (all expected cycles done, complete outcomes);
- failure-mode recurrence -> recurred True (non-complete outcome `max_steps_reached`,
  `error`);
- gaps feed the verdict (a cycle with no marker -> recurred True);
- in-flight cycle -> recurred True;
- no trajectory file -> empty outcomes -> clean when all done;
- expected cycles = union of the diagnosis's cycle sets (first-seen order);
- failure_mode reported verbatim;
- custom markers / read_cycles_out / read_trajectory seams;
- to_dict/from_dict round-trip + to_dict keys.
- Use injectable seams / `patch.object` — never constructor-level patches; never touch
  the real filesystem.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
