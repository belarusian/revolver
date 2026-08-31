"""revolver.fixes — concrete per-failure-mode fix builders.

Diff from predecessor: each actionable builder now emits TWO NEW files — the
existing plan file PLUS a NEW ``<mode>_cycles.out`` marker file (the marker is
the cycles.out append the launch plan would record). The healthy ("none") builder
still emits an empty repair path.
Evidence: sentry/cli.py defines the three actionable failure modes — driver-death
(driver process dead), wall-kill-no-merge (a cycle wall-killed without merging),
and stall (inner PID hung; kill the inner PID only, NEVER the driver). Each builder
here emits a minimal NEW-file-only repair path for one failure mode.

Deterministic, stdlib-only, pure functions. No disk writes, no process launch.
Every generated file's content embeds a docstring stating "Diff from predecessor:
..." and "Evidence: ..." (the house convention used in diagnosis.py /
sentry_client.py).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from revolver.diagnosis import Diagnosis
from revolver.proposal import PROPOSAL_NAMESPACE, NewFile

# The generated-file paths for a given failure mode (always under the proposal
# namespace so the repair path is additions-only). Each mode has a plan file and a
# cycles.out marker file.
_PLAN_PATHS = {
    "driver-death": PROPOSAL_NAMESPACE + "driver_death_relaunch.py",
    "wall-kill": PROPOSAL_NAMESPACE + "wall_kill_remerge.py",
    "stall-kill": PROPOSAL_NAMESPACE + "stall_inner_kill.py",
}
_MARKER_PATHS = {
    "driver-death": PROPOSAL_NAMESPACE + "driver-death_cycles.out",
    "wall-kill": PROPOSAL_NAMESPACE + "wall-kill_cycles.out",
    "stall-kill": PROPOSAL_NAMESPACE + "stall-kill_cycles.out",
}


def _content(diff: str, evidence: str, body: str) -> str:
    """Assemble a generated file's content with the required docstring.

    The docstring states the diff-from-predecessor and the motivating evidence,
    followed by a deterministic body.
    """
    return (
        '"""Generated repair file (additions only; hard rule 7: never mutate).\n'
        "\n"
        f"Diff from predecessor: {diff}\n"
        f"Evidence: {evidence}\n"
        '"""\n'
        "\n"
        f"{body}\n"
    )


def _marker_content(diff: str, evidence: str, marker_line: str) -> str:
    """Assemble a cycles.out marker file's content.

    The marker file carries the same required docstring plus the single marker
    line that would be appended to ``cycles.out`` on launch.
    """
    return (
        '"""Generated cycles.out marker (additions only; hard rule 7: never mutate).\n'
        "\n"
        f"Diff from predecessor: {diff}\n"
        f"Evidence: {evidence}\n"
        '"""\n'
        "\n"
        f"{marker_line}\n"
    )


def build_driver_death_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for a dead driver process.

    Pure, deterministic, stdlib-only. Emits a relaunch-plan file PLUS a
    ``driver-death_cycles.out`` marker file (no process is actually launched here
    — that is cycles 8-9).
    """
    cycle = diagnosis.driver_death_cycle
    diff = (
        f"NEW relaunch-plan file for the dead driver (cycle {cycle}); no predecessor "
        "file existed, so the diff is the entire file."
    )
    evidence = (
        f"driver-death DETECTED cycle {cycle}; driver_alive={diagnosis.driver_alive}; "
        f"source={diagnosis.source}; {diagnosis.evidence}"
    )
    body = (
        f"# relaunch plan for driver death (cycle {cycle})\n"
        f"PIPELINE_ID = {diagnosis.pipeline_id!r}\n"
        f"ENDPOINT_PIN = {diagnosis.endpoint_pin!r}\n"
        f"DEAD_CYCLE = {cycle}\n"
    )
    marker_line = f"= LAUNCH {diagnosis.pipeline_id} driver-death =\n"
    marker_diff = (
        f"NEW cycles.out marker for the dead driver (cycle {cycle}); no predecessor "
        "file existed, so the diff is the entire file."
    )
    return [
        NewFile(
            path=_PLAN_PATHS["driver-death"],
            content=_content(diff, evidence, body),
            diff_from_predecessor=diff,
            evidence=evidence,
        ),
        NewFile(
            path=_MARKER_PATHS["driver-death"],
            content=_marker_content(marker_diff, evidence, marker_line),
            diff_from_predecessor=marker_diff,
            evidence=evidence,
        ),
    ]


def build_wall_kill_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for a wall-killed cycle that never merged.

    Pure, deterministic, stdlib-only. Emits a remerge-plan file PLUS a
    ``wall-kill_cycles.out`` marker file.
    """
    cycle = diagnosis.wall_kill_cycle
    diff = (
        f"NEW remerge-plan file for the wall-killed cycle {cycle}; no predecessor "
        "file existed, so the diff is the entire file."
    )
    evidence = (
        f"wall-kill-no-merge DETECTED cycle {cycle}; "
        f"wall_kill cycles={diagnosis.cycles_wall_kill}; source={diagnosis.source}; "
        f"{diagnosis.evidence}"
    )
    body = (
        f"# remerge plan for wall-kill (cycle {cycle})\n"
        f"PIPELINE_ID = {diagnosis.pipeline_id!r}\n"
        f"WALL_KILL_CYCLE = {cycle}\n"
        f"WALL_KILL_CYCLES = {diagnosis.cycles_wall_kill!r}\n"
    )
    marker_line = f"= LAUNCH {diagnosis.pipeline_id} wall-kill =\n"
    marker_diff = (
        f"NEW cycles.out marker for the wall-killed cycle {cycle}; no predecessor "
        "file existed, so the diff is the entire file."
    )
    return [
        NewFile(
            path=_PLAN_PATHS["wall-kill"],
            content=_content(diff, evidence, body),
            diff_from_predecessor=diff,
            evidence=evidence,
        ),
        NewFile(
            path=_MARKER_PATHS["wall-kill"],
            content=_marker_content(marker_diff, evidence, marker_line),
            diff_from_predecessor=marker_diff,
            evidence=evidence,
        ),
    ]


def build_stall_kill_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for a stalled inner PID.

    Pure, deterministic, stdlib-only. Emits an inner-PID kill-plan file (kill the
    inner PID only, NEVER the driver — that stays sentry's) PLUS a
    ``stall-kill_cycles.out`` marker file.
    """
    diff = (
        "NEW inner-PID kill-plan file for a stalled inner process; no predecessor "
        "file existed, so the diff is the entire file."
    )
    evidence = (
        f"stall action={diagnosis.stall_action!r} reason={diagnosis.stall_reason!r}; "
        f"live_work={diagnosis.live_work} root={diagnosis.live_work_root}; "
        f"source={diagnosis.source}; {diagnosis.evidence}"
    )
    body = (
        f"# inner-PID kill plan for stall (never the driver)\n"
        f"PIPELINE_ID = {diagnosis.pipeline_id!r}\n"
        f"STALL_ACTION = {diagnosis.stall_action!r}\n"
        f"STALL_REASON = {diagnosis.stall_reason!r}\n"
        f"LIVE_WORK_ROOT = {diagnosis.live_work_root!r}\n"
    )
    marker_line = f"= LAUNCH {diagnosis.pipeline_id} stall-kill =\n"
    marker_diff = (
        "NEW cycles.out marker for a stalled inner process; no predecessor file "
        "existed, so the diff is the entire file."
    )
    return [
        NewFile(
            path=_PLAN_PATHS["stall-kill"],
            content=_content(diff, evidence, body),
            diff_from_predecessor=diff,
            evidence=evidence,
        ),
        NewFile(
            path=_MARKER_PATHS["stall-kill"],
            content=_marker_content(marker_diff, evidence, marker_line),
            diff_from_predecessor=marker_diff,
            evidence=evidence,
        ),
    ]


def build_none_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """Healthy diagnosis -> empty repair path (no-op proposal)."""
    return []




# ---------------------------------------------------------------------------
# Founding fix-class generators (Cycle 14)
# ---------------------------------------------------------------------------
#
# The two founding use cases from Revolver-task.md, implemented as pure,
# deterministic, data-driven builders. They synthesize ORIGINAL code (never copy
# the golden reference files) whose SEMANTIC shape matches the hand-built v3 set:
#   * client-timeout (sentry cycle 8): an explicit litellm request timeout so the
#     client never cancels a long inference before the external wall.
#   * inner-wall (sentry cycle 11): a wall-kill AFTER the cycle merged -> raise the
#     inner wall (--inner-seconds), everything else byte-identical.
#
# Every generated file's content embeds "Diff from predecessor: ..." and
# "Evidence: ..." (the house convention). All paths are under PROPOSAL_NAMESPACE
# (hard rule 7: additions only, never a mutation).

# Default explicit LLM request timeout (seconds). Larger than any current external
# wall (max 10800s) so the driver-supplied wall stays the sole timekeeper.
_DEFAULT_REQUEST_TIMEOUT = 21600

# Stated margin (seconds) added over the observed heaviest inner duration (or the
# old inner wall) when deriving the corrected --inner-seconds for the inner-wall fix.
_INNER_WALL_MARGIN = 1800

# Default inner wall (seconds) used when the diagnosis carries no inner_seconds.
_DEFAULT_INNER_SECONDS = 3000

# Default outer wall (seconds) used when the diagnosis carries no outer_wall.
_DEFAULT_OUTER_WALL = 10800


def _client_timeout_evidence(diagnosis: Diagnosis) -> str:
    """The cycle-8 evidence string shared by all four generated files."""
    cycle = diagnosis.client_timeout_cycle
    return (
        f"sentry cycle {cycle} (2026-08-25): context grew past context_limit "
        "(normal), escalated to the deep model; at ~76k-token context a single "
        "completion takes >10 min (~17 t/s). No explicit request timeout anywhere "
        "-> litellm's built-in default (~600s) cancelled the request CLIENT-side "
        "mid-generation (llama.cpp 'W srv stop: cancel task' at n_gen~10k, instant "
        "same-prefix relaunch). Stacked retries (litellm num_retries x tenacity x10) "
        "re-sent the full context and died again ~30 times; the external wall then "
        "SIGTERMed the process mid-retry -> no trajectory written. "
        f"source={diagnosis.source}; {diagnosis.evidence}"
    )


def build_client_timeout_fix(
    diagnosis: Diagnosis,
    *,
    triple_dir: str | Path | None = None,
) -> list[NewFile]:
    """NEW-file-only repair path for the client-timeout (cancel-loop) failure mode.

    Thin instruction emitter over ``revolver.derive``: composes four
    ``ChangeInstruction`` objects (one per file) and calls ``derive()`` for each.
    Predecessors are resolved from the triple meta dir by PATH — no embedded
    module bodies.
    Args:
        diagnosis: The failure diagnosis.
        triple_dir: Overridable seam for the triple meta directory. When
            ``None`` (default) the canonical path
            ``~/AI/revolver/triple`` is used. Supply a custom path to
            point at a test fixture or alternate triple.

    Pure, deterministic, stdlib-only. No disk writes, no clock, no randomness.
    """
    from pathlib import Path

    from revolver.derive import ChangeInstruction, derive

    evidence = _client_timeout_evidence(diagnosis)
    outer_wall = diagnosis.outer_wall or _DEFAULT_OUTER_WALL
    request_timeout = max(_DEFAULT_REQUEST_TIMEOUT, outer_wall)

    # Resolve predecessor paths from the triple meta dir.
    triple_dir = Path(triple_dir) if triple_dir is not None else Path.home() / "AI" / "revolver" / "triple"
    chat_model_pred = triple_dir / "chat_model.py"
    runner_pred = triple_dir / "run-v3.py"
    spoke_pred = triple_dir / "cycle-implementation-v4.py"
    driver_pred = triple_dir / "run-cycles-v3.sh"

    # -- 1. chat-model: replace the pinned 600s default with an env-driven timeout --
    # ONE line, pure value replacement (the shape derive() verifies cleanly): the
    # predecessor pins request_timeout to litellm's built-in ~600s default -- the
    # cycle-8 cancel-loop -- and the derived variant reads it from the environment.
    chat_model_instr = ChangeInstruction(
        kind="replace-value",
        target="    request_timeout = 600  # litellm built-in default — the cycle-8 cancel-loop",
        replacement='    request_timeout = int(os.getenv("FIVE_REQUEST_TIMEOUT", "21600"))',
        new_name="client_timeout_chat_model.py",
        evidence=evidence,
    )
    chat_model_variant = derive(chat_model_pred, chat_model_instr)

    # -- 2. runner: annotate the import (predecessor already has the v2 import) --
    runner_instr = ChangeInstruction(
        kind="annotate-import",
        target="from four.chat_model_v2 import context_aware_invoke",
        replacement="from four.chat_model_v2 import context_aware_invoke  # client-timeout: explicit request timeout",
        new_name="client_timeout_runner.py",
        evidence=evidence,
    )
    runner_variant = derive(runner_pred, runner_instr)

    # -- 3. spoke: annotate the import (predecessor already has the v2 import) --
    spoke_instr = ChangeInstruction(
        kind="annotate-import",
        target="from four.chat_model_v2 import context_aware_invoke",
        replacement="from four.chat_model_v2 import context_aware_invoke  # client-timeout: explicit request timeout",
        new_name="client_timeout_spoke.py",
        evidence=evidence,
    )
    spoke_variant = derive(spoke_pred, spoke_instr)

    # -- 4. driver: annotate the export (predecessor already has the export) --
    driver_instr = ChangeInstruction(
        kind="annotate-export",
        target="export FIVE_REQUEST_TIMEOUT=21600",
        replacement=f"export FIVE_REQUEST_TIMEOUT={request_timeout}  # client-timeout: >= {outer_wall}s outer wall",
        new_name="client_timeout_driver.sh",
        evidence=evidence,
    )
    driver_variant = derive(driver_pred, driver_instr)

    # Convert DerivedVariant objects to NewFile objects.
    return [
        NewFile(
            path=PROPOSAL_NAMESPACE + v.path,
            content=v.content,
            diff_from_predecessor=v.diff_from_predecessor,
            evidence=v.evidence,
        )
        for v in (chat_model_variant, runner_variant, spoke_variant, driver_variant)
    ]

def build_inner_wall_fix(
    diagnosis: Diagnosis,
    *,
    predecessor_driver: str | None = None,
) -> list[NewFile]:
    """NEW-file-only repair path for the inner-wall failure mode (wall-kill AFTER merge).

    Emits ONE new file — a driver variant whose ONLY delta is a larger
    --inner-seconds. This builder is a THIN INSTRUCTION EMITTER over
    ``revolver.derive``: it composes a single ``ChangeInstruction``
    (replace the --inner-seconds value) and hands the predecessor PATH to
    ``derive()``, which reads the file read-only, applies the edit, and
    verifies by construction (compile + diff == stated lines).

    The new inner-seconds value is derived from the observed heaviest inner duration
    when the diagnosis carries one (plus a stated margin), else a stated margin over
    the old value.

    Pure, deterministic, stdlib-only. No disk writes, no clock, no randomness.
    The predecessor is referenced by PATH (never embedded as text).

    Predecessor resolution (TICKET-087): ``predecessor_driver`` is the PATH to the
    predecessor driver file. When it is omitted (``None``), the builder falls back
    to ``diagnosis.inner_wall_driver_path``; if that is also ``None`` it raises
    ``ValueError`` (no predecessor path available). Passing ``predecessor_driver``
    explicitly always wins and keeps the prior behavior byte-identical.
    """
    from pathlib import Path

    from revolver.derive import ChangeInstruction, derive

    # Resolve the predecessor driver PATH (TICKET-087): an explicit
    # predecessor_driver= always wins; otherwise fall back to the diagnosis
    # field; otherwise fail loud.
    if predecessor_driver is None:
        predecessor_driver = diagnosis.inner_wall_driver_path
    if predecessor_driver is None:
        raise ValueError(
            "build_inner_wall_fix: no predecessor driver path available "
            "(pass predecessor_driver= or set diagnosis.inner_wall_driver_path)"
        )

    cycle = diagnosis.inner_wall_kill_cycle
    evidence = (
        f"sentry cycle {cycle} (2026-08-27): a heavy cycle was wall-killed AFTER it "
        "had already merged — the inner wall (--inner-seconds) was too small for the "
        "heaviest cycle, so the driver's inner timeout SIGTERMed the inner process "
        "mid-cycle even though the work had landed. Distinguish from wall-kill-no-merge "
        "by the PRESENCE of the merge: the merge commit is on main, so the repair is to "
        "raise the inner wall, not to re-merge. "
        f"source={diagnosis.source}; {diagnosis.evidence}"
    )

    # Derive the corrected inner wall.
    if diagnosis.heaviest_inner_duration is not None:
        old_inner = diagnosis.heaviest_inner_duration
    else:
        old_inner = diagnosis.inner_seconds or _DEFAULT_INNER_SECONDS
    new_inner = old_inner + _INNER_WALL_MARGIN

    # Compose the single stated edit (DATA, not code).
    instruction = ChangeInstruction(
        kind="replace-value",
        target=f"--inner-seconds {old_inner}",
        replacement=f"--inner-seconds {new_inner}",
        new_name=PROPOSAL_NAMESPACE + "inner_wall_driver.sh",
        evidence=evidence,
    )

    # Derive by reference: read the predecessor PATH, apply the edit, verify.
    variant = derive(Path(predecessor_driver), instruction)

    return [
        NewFile(
            path=variant.path,
            content=variant.content,
            diff_from_predecessor=variant.diff_from_predecessor,
            evidence=variant.evidence,
        ),
    ]


# ---------------------------------------------------------------------------
# Outer-freshness fix-class generator (Cycle 16)
# ---------------------------------------------------------------------------
#
# The fleet's newest observed failure class: UNWITNESSED INNER DEATH /
# stale-trajectory-slot. The inner pass dies (rc=124, EMPTY output — wall-kill
# before emit, block-buffered stdout lost) and NO trajectory newer than the
# pass-start snapshot exists. The predecessor runner's step-2 read (run-v3.py:84,
# "READ its trajectory: the newest .json") has NO branch for "nothing new this
# pass", so the outer globs the newest .json, reads a PRIOR cycle's
# exit:task_complete DONE, accepts completion, and wanders to max_steps.
#
# build_outer_freshness_fix takes the run-v3.py predecessor text READ-ONLY (input
# only — it is NEVER copied and NEVER written to ~/Research/four) and emits NEW
# run-v4.py content whose step-2 read is pass-freshness-guarded: the newest
# trajectory must be NEWER than the pass-start snapshot; no new sequence =>
# dead-unwitnessed => re-invoke or do the work yourself => the stale newest file
# is NEVER evidence of completion. It also emits a driver-variant template
# (RUN=.../run-v4.py, endpoints verbatim, FIVE_REQUEST_TIMEOUT >= outer wall)
# reusing the launch-plan budget machinery.
#
# The physical run-v4.py birth happens at revolver APPLY time, under the manifest
# — never by this cycle.

# The generated runner's path (under the proposal namespace; additions only).
_OUTER_FRESHNESS_RUNNER_PATH = PROPOSAL_NAMESPACE + "outer_freshness_run_v4.py"


def _outer_freshness_evidence(diagnosis: Diagnosis) -> str:
    """The cycle-16 evidence string shared by all generated files."""
    base_seq = diagnosis.pass_start_max_seq
    return (
        "spoke-lint cycle 15 (trajectory_0027 msgs [2]-[3]: inner rc=124 with "
        "EMPTY output - wall-kill before emit, block-buffered stdout lost - then "
        "the outer read the newest .json, trajectory_0026, an Aug-19 cycle-12 "
        "DONE, accepted it, wandered to max_steps) and revolver cycle 14 "
        "(trajectory_0029 msgs [2]-[3]: identical signature - rc=124 empty, read "
        "trajectory_0028's DONE, max_steps). Defect line: run-v3.py:84 task "
        'template ("READ its trajectory: the newest .json ...") with no branch '
        'for "nothing new this pass". '
        f"pass_start_max_seq={base_seq}; source={diagnosis.source}; "
        f"{diagnosis.evidence}"
    )


def build_outer_freshness_fix(
    diagnosis: Diagnosis,
    *,
    predecessor_runner: str,
) -> list[NewFile]:
    """NEW-file-only repair path for the outer-freshness (unwitnessed inner death) mode.

    Thin instruction emitter over ``revolver.derive``: composes two
    ``ChangeInstruction`` objects (one per file) and calls ``derive()`` for each.
    Predecessors are resolved from the triple meta dir by PATH — no embedded
    module bodies.

    Emits TWO NEW files, each under PROPOSAL_NAMESPACE, each carrying a docstring
    stating diff-from-predecessor + the cycle-16 evidence (trajectory_0027 /
    trajectory_0029, run-v3.py:84):

      1. ``outer_freshness_run_v4.py`` - the run-v3 runner with its step-2
         trajectory read pass-freshness-guarded: the newest trajectory must be
         NEWER than the pass-start snapshot; no new sequence => dead-unwitnessed
         => re-invoke or do the work yourself => the stale newest file is NEVER
         evidence of completion.
      2. ``outer_freshness_driver.sh`` - the driver with RUN repointed at the
         generated run-v4 runner (which carries the guard).

    Pure, deterministic, stdlib-only. No disk writes, no clock, no randomness.
    """
    from pathlib import Path

    from revolver.derive import ChangeInstruction, derive

    # ``predecessor_runner`` is retained for signature compatibility; the
    # predecessor is now resolved by PATH from the triple meta dir (artifacts
    # carry references, never values).
    _ = predecessor_runner

    evidence = _outer_freshness_evidence(diagnosis)

    # Resolve predecessor paths from the triple meta dir (references, not values).
    triple_dir = Path.home() / "AI" / "revolver" / "triple"
    runner_pred = triple_dir / "outer_freshness_run_v3.py"
    driver_pred = triple_dir / "outer_freshness_driver_v3.sh"

    # -- 1. runner: guard the step-2 trajectory read (the ONE semantic edit) --
    # The predecessor's step-2 read is unguarded (before-state); the derived
    # variant branches on the pass-freshness guard so a stale newest file is
    # never accepted as completion.
    runner_instr = ChangeInstruction(
        kind="guard-step2-read",
        target="    newest = read_newest_trajectory(str(trajectories))  # step-2: unguarded (before-state)",
        replacement=(
            "    if not pass_freshness_guard(str(trajectories), pass_start_max_seq):\n"
            "        # No trajectory NEWER than the pass-start snapshot: the inner pass died\n"
            "        # unwitnessed (rc=124, EMPTY output). The stale newest file is NEVER\n"
            "        # evidence of completion. Re-invoke the inner OR do the work yourself.\n"
            "        print(\n"
            '            "DEAD-UNWITNESSED: no new trajectory this pass; re-invoke or do the "\n'
            '            "work yourself (never accept the stale newest file as completion)"\n'
            "        )\n"
            "        sys.exit(124)\n"
            "    newest = read_newest_trajectory(str(trajectories))"
        ),
        new_name="outer_freshness_run_v4.py",
        evidence=evidence,
    )
    runner_variant = derive(runner_pred, runner_instr)

    # -- 2. driver: repoint RUN at the generated run-v4 runner --
    driver_instr = ChangeInstruction(
        kind="repoint-run",
        target="RUN=/home/sasha/AI/revolver/triple/run-v3.py",
        replacement="RUN=" + _OUTER_FRESHNESS_RUNNER_PATH,
        new_name="outer_freshness_driver.sh",
        evidence=evidence,
    )
    driver_variant = derive(driver_pred, driver_instr)

    # Convert DerivedVariant objects to NewFile objects.
    return [
        NewFile(
            path=PROPOSAL_NAMESPACE + v.path,
            content=v.content,
            diff_from_predecessor=v.diff_from_predecessor,
            evidence=v.evidence,
        )
        for v in (runner_variant, driver_variant)
    ]


# Registry keyed by failure_mode; unknown modes fall back to the none-builder.
# (The inner-wall builder is registered: its predecessor_driver is now optional
# and falls back to diagnosis.inner_wall_driver_path, so it is callable with a
# single argument via propose(). The outer-freshness builder still takes a
# keyword-only predecessor_runner and is NOT in this single-arg registry; it is
# called directly with the predecessor text.)
FIX_BUILDERS: dict[str, Callable[[Diagnosis], list[NewFile]]] = {
    "driver-death": build_driver_death_fix,
    "wall-kill": build_wall_kill_fix,
    "stall-kill": build_stall_kill_fix,
    "client-timeout": build_client_timeout_fix,
    "inner-wall": build_inner_wall_fix,
    "none": build_none_fix,
}
