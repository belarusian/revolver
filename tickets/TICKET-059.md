# TICKET-059 — tests/test_observe.py extension (merge-commit + final-report coverage)

Status: DONE
## Capability
Extend `tests/test_observe.py` with the Cycle 12 coverage.

## Spec
- `parse_merge_commits`: single commit, multiple, file order, no reorder/dedupe, empty, custom merge_pattern seam, no-match -> empty.
- `observe_git`: all merged, some missing, empty cycles, custom merge_commits/read_git_log seams, injected reader means default never called.
- `render_final_report` + `render`: clean run -> recurred False + render text, recurrence -> recurred True, git missing feeds the report, empty inputs, custom markers/read_cycles_out/read_trajectory/merge_commits/read_git_log seams, render deterministic + embeds each section + stable across round-trip.
- Use injectable seams / `patch.object` — never constructor-level patches; never touch the real filesystem.

## Acceptance
- full suite green; ruff clean; mypy clean.

DONE — verified implemented in observe.py (tests in test_observe.py); closed out in Cycle 36.
