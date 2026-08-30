# TICKET-086 — No dedicated structural-contract unit test module for build_client_timeout_fix / build_inner_wall_fix

**Status:** DONE
**Cycle:** 32 (synthesis audit)
**Parent:** TICKET-069

## Evidence

TICKET-069 (tickets/TICKET-069.md) specifies a unit-test module covering the
structural contract of the two founding fix generators. The test suite contains:

- `tests/test_replay.py` — replay *acceptance* tests (TICKET-067): asserts
  semantic equivalence to the golden reference, execution-based validation
  (py_compile, import resolution, driver parsing, diff isolation).
- No `tests/test_fixes.py` exists.

The structural contract items TICKET-069 lists are partially covered by
test_replay.py but not as a dedicated unit-test module:

| Contract item (TICKET-069) | test_replay.py coverage | Gap |
|---|---|---|
| client-timeout: exactly 4 NEW files | `test_emits_four_new_files` (line 75) | Covered |
| client-timeout: all paths under PROPOSAL_NAMESPACE | `test_emits_four_new_files` (line 77) | Covered |
| client-timeout: every content embeds "Diff from predecessor:" + "Evidence:" | Not asserted as a systematic invariant | **Missing** |
| client-timeout: chat-model passes timeout to BOTH impls | `test_chat_model_passes_timeout_to_both_impls` (line 193) | Covered |
| client-timeout: runner + spoke carry one-line import delta | `test_diff_isolation` (line 162) covers chat-model only | **Missing for runner/spoke** |
| client-timeout: driver exports FIVE_REQUEST_TIMEOUT >= outer wall + repoints RUN/SPOKE | `test_driver_exports_timeout_ge_outer_wall_and_repoints` (line 215) | Covered |
| client-timeout: pure + deterministic | Not tested | **Missing** |
| inner-wall: exactly 1 NEW file | `test_emits_one_new_file` (line 270) | Covered |
| inner-wall: only delta is --inner-seconds | `test_only_delta_is_inner_seconds` (line 276) | Covered |
| inner-wall: new value from heaviest when present, else margin over old | `test_margin_over_old_when_no_heaviest` (line 313) | Covered |
| inner-wall: pure + deterministic | Not tested | **Missing** |
| Both builders registered in FIX_BUILDERS + reachable via propose() | `test_propose_yields_client_timeout_path` (line 232) covers client-timeout only | **Missing for inner-wall** (see TICKET-087) |

## Impact

TICKET-069 cannot be closed without a dedicated unit-test module. The replay
tests are execution-plane-dependent (they require `~/AI/revolver/triple/` for
client-timeout) and assert semantic equivalence to golden references — a
different test concern than the structural contract. A validator spoke cannot
verify TICKET-069's acceptance criteria against the existing test suite.

## Suggestion

Create `tests/test_fixes.py` with a `TestClientTimeoutContract` class and a
`TestInnerWallContract` class. Each test is pure (no triple directory required
for inner-wall; client-timeout tests that need the triple dir are marked
`@requires_triple`). The structural invariants to assert:

1. File count (4 / 1).
2. All paths under `PROPOSAL_NAMESPACE`.
3. Every `NewFile.content` contains both `"Diff from predecessor:"` and
   `"Evidence:"` (the house docstring contract).
4. Determinism: calling the builder twice with the same `Diagnosis` produces
   identical `list[NewFile]` (compare by `to_dict()`).
5. For inner-wall: the `--inner-seconds` derivation logic (heaviest + margin
   vs old + margin) is asserted at the unit level with controlled inputs.
6. For client-timeout: the runner and spoke each carry exactly one import
   annotation delta (not just the chat-model).
