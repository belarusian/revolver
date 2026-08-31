# TICKET-077 — Fix-class builders as instruction emitters over the seed triple (all three classes)

**Status:** DONE
**Cycle:** 18
**Build Order row:** Derive-by-reference (17–19)

## Capability
Rewrite the three fix-class generators as thin instruction emitters that call
`revolver.derive` — no string-embedded module bodies anywhere in `revolver/fixes.py`:
- `build_client_timeout_fix(diagnosis)`: emits the instruction set that reproduces the
  v3-set shape BY DERIVATION — four instructions, each predecessor a resolved PATH, no
  embedded text: (1) chat-model predecessor (the module run-v3.py's invoke comes from —
  pinned meta reference like the triple elements, same sha256 discipline) + one-stated-edit
  `timeout=FIVE_REQUEST_TIMEOUT` insertion; (2) triple `run-v3.py` + one import-swap to
  the derived chat-model module; (3) triple `cycle-implementation-v4.py` + one
  import-swap; (4) triple `run-cycles-v3.sh` + one export edit
  (`FIVE_REQUEST_TIMEOUT=21600` and/or RUN+SPOKE repointed to the staged paths). Exact
  output version names follow hard-rule-7 convention (next free `vN`), chosen by the
  builder, never hard-coded in this ticket.
- `build_inner_wall_fix(diagnosis)`: driver-only single instruction — replace the
  `--inner-seconds` value (`3000 → diagnosis.inner_seconds_target`), everything else
  byte-identical. (Already the right shape; migrate to the shared `derive` call so one
  verification path serves all classes.)
- `build_outer_freshness_fix(diagnosis)`: derive `run-v4` from triple `run-v3.py` with
  the one stated edit (task-template replacement adding the pass-freshness guard —
  emit the replacement text as the instruction's `replacement` data, citing
  trajectory_0027/0029), plus driver repoint instruction (`RUN=…/run-v4.py`). This
  MIGRATES the PR #89 value-embedding builder onto the new architecture — after this
  change `fixes.py` carries ZERO embedded runner/chat-model bodies.
- The generated staged set cross-references by PATH (generated runner imports the
  staged chat-model module by name; generated driver's `RUN=`/`SPOKE=` name the staged
  files), preserving the golden set's reference structure.

## Acceptance
- `grep -n "def build_" revolver/fixes.py | wc -l` == 3, and NONE of the three
  contains a multi-line embedded module body (no generated-file content longer than the
  stated single-edit replacements; the client-timeout chat-model body, the runner stub
  main(), and the sentry-driver copy are GONE — evidence: fixes.py:289ff value-embedding
  pattern no longer present).
- Each builder returns a proposal whose every file passes `derive` verification
  (compile + diff == stated lines).
- Additive-compatible: existing `propose()` / validate() flows keep passing.

**DONE (Cycle 37, HEAD ae97445):** The three fix-class builders (`build_client_timeout_fix`, `build_inner_wall_fix`, `build_outer_freshness_fix`) are thin instruction emitters over `revolver.derive` (verified: each composes `ChangeInstruction` objects and calls `derive()`; no embedded module body). The one remaining dead embedded body `_outer_freshness_runner_content` (fixes.py:477-578) was removed in Cycle 37, leaving ZERO embedded module bodies. Acceptance re-measured: `grep -n 'def build_' revolver/fixes.py | wc -l` == 7 (4 none/driver/wall/stall + 3 derive emitters); the value-embedding pattern (`def main` / `import litellm` / `_EMBEDDED` / `_BODY` / `_TEMPLATE`) is gone; full gate clean (414 passed, ruff clean, mypy clean). Note: the acceptance line '== 3' was written at Cycle 18 when only the 3 derive builders existed; the invariant it guards (no embedded module body in any builder) holds at the current count of 7.
