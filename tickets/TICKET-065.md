# TICKET-065: client-timeout fix-class generator (sentry cycle 8)

**Found:** 2026-08-27, operator re-prime (Build Order row "Fix-class templates + replay acceptance | 14-15").
**Status:** Open — founding use case 1 of Revolver-task.md is not implemented.
**Severity:** high — the hard replay acceptance test.

## Evidence

Revolver-task.md founding use case 1: given a sentry diagnosis of "client-side request
timeout cancelling long inferences; stacked retries re-sending full context; wall kills
process mid-retry; no trajectory", revolver must PRODUCE the equivalent of the hand-built
v3 path. The current `revolver/fixes.py` has builders for sentry's three actionable
failure modes (driver-death / wall-kill / stall-kill) emitting generic plan-file +
marker-file pairs, but NO builder for this class. `grep -rn FIVE_REQUEST_TIMEOUT revolver/`
returns nothing: the cycle-8 fix exists only as the abstract `request_timeout >= outer_wall`
invariant in `launch_plan.py`, not as a file-generation template.

The incident (sentry cycle 8, 2026-08-25): context grew past context_limit (normal),
escalated to the deep model; at ~76k-token context a single completion takes >10 min
(~17 t/s). No explicit request timeout anywhere in our code -> litellm's built-in default
(~600s) cancelled the request CLIENT-side mid-generation (llama.cpp: "W srv stop: cancel
task" at n_gen~10k, instant same-prefix relaunch). Stacked retries (litellm num_retries x
tenacity x10) re-sent the full context and died again ~30 times; the external wall then
SIGTERMed the process mid-retry -> no trajectory written.

The golden reference (what a correct generator must reproduce, semantically):
- `/home/sasha/Research/four/src/four/chat_model_v2.py` — new module; ONE change vs
  chat_model.py: context_aware_invoke passes an explicit litellm request timeout (env
  FIVE_REQUEST_TIMEOUT, default 21600s) to both impls via model_kwargs. Docstring states
  the diff + the cycle-8 evidence.
- `/home/sasha/Research/four/run-v3.py` — new runner; ONE-line import delta vs run-v2.py:
  context_aware_invoke now comes from four.chat_model_v2. Everything else byte-identical.
- `/home/sasha/Research/four/examples/spokes/cycle-implementation-v4.py` — new spoke
  variant; ONE-line import delta vs cycle-implementation.py (same fix). Lineage note:
  2-LLM line, unrelated to the single-LLM -v3.
- `/home/sasha/AI/sentry/run-cycles-v3.sh` — driver variant: RUN -> run-v3.py, SPOKE ->
  cycle-implementation-v4.py, export FIVE_REQUEST_TIMEOUT=21600 (> the driver's outer
  wall, so the external wall stays the sole timekeeper). Header states the diff + why.

All four golden files are READ-ONLY references (the seed discipline): synthesize original
code, never copy files into the repo.

## Impact

Without this builder, revolver cannot close the loop for the failure class that created
it: sentry diagnoses the cancel-loop, but revolver has no versioned repair path to
propose for it. The founding acceptance test of the project is unrunnable.

## Suggestion

- New builder in `revolver/fixes.py` (or a new module if cleaner): given a Diagnosis of
  the client-timeout class, emit the NEW-file-only set: timeout module + runner variant +
  spoke variant + driver variant. Every generated file carries a docstring stating its
  diff from the predecessor and the evidence motivating it (the house convention).
- The diagnosis side must be able to CARRY this failure mode: `parse_sentry_report` /
  `_derive_failure_mode` currently derive only driver-death / wall-kill / stall-kill /
  none. Extend the Diagnosis (additively) with a field for the inference-cancel evidence
  (e.g. from a sentry report line or operator-supplied evidence text) so the class is
  addressable; keep the existing four modes byte-compatible.
- Replay acceptance test: cycle-8 diagnosis in -> generated path; assert semantic
  equivalence to the golden set (the explicit-timeout import delta present, the driver
  exports FIVE_REQUEST_TIMEOUT >= outer wall, docstrings carry diff + evidence).
