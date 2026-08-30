# TICKET-089 — Content docstring contract ("Diff from predecessor:" + "Evidence:") not asserted as a structural invariant

**Status:** DONE
**Cycle:** 32 (synthesis audit)
**Parent:** TICKET-069

## Evidence

TICKET-069 states:
> every content embeds "Diff from predecessor:" + "Evidence:"

The `NewFile` dataclass (proposal.py line 44-50) documents:
> content: The file's text. Must embed a docstring stating
>     "Diff from predecessor: ..." and "Evidence: ...".

The module docstring of fixes.py (line 1-14) states:
> Every generated file's content embeds a docstring stating "Diff from
> predecessor: ..." and "Evidence: ..." (the house convention used in
> diagnosis.py / sentry_client.py).

However, no test systematically asserts this contract across ALL generated
files. The replay tests check specific content properties (timeout values,
import lines, inner-seconds) but never assert that every `NewFile.content`
contains both required docstring markers.

For `build_client_timeout_fix`: 4 files are generated. The replay tests check
the chat-model's timeout, the driver's export, the runner's import — but do
not assert the docstring contract on all 4.

For `build_inner_wall_fix`: 1 file is generated. The replay tests check the
inner-seconds value but do not assert the docstring contract.

## Impact

A regression that drops the docstring from a generated file (e.g., a refactor
of `_content()` or `derive()` that changes the header format) would not be
caught. The docstring is the version-chain mechanism: each generated file
names its predecessor by PATH in the docstring. Without it, the version chain
is broken and the file cannot be traced back to its source.

## Suggestion

Add to `tests/test_fixes.py`: