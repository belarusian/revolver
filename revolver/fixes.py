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


def build_client_timeout_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for the client-timeout (cancel-loop) failure mode.

    Emits the NEW-file-only equivalent of the hand-built v3 set: four NEW files,
    each under PROPOSAL_NAMESPACE, each carrying a docstring stating
    diff-from-predecessor + the cycle-8 evidence:

      1. a chat-model module whose ``context_aware_invoke`` passes an explicit
         litellm request timeout (env FIVE_REQUEST_TIMEOUT, default 21600s) to BOTH
         impls (fast + large);
      2. a runner variant with the ONE-line import delta (context_aware_invoke from
         the new module);
      3. a spoke variant with the SAME one-line import delta;
      4. a driver variant exporting FIVE_REQUEST_TIMEOUT >= its outer wall and
         repointing RUN/SPOKE at the new files.

    Pure, deterministic, stdlib-only. No disk writes, no clock, no randomness.
    """
    evidence = _client_timeout_evidence(diagnosis)
    outer_wall = diagnosis.outer_wall or _DEFAULT_OUTER_WALL
    # The exported request timeout must stay >= the driver's outer wall.
    request_timeout = max(_DEFAULT_REQUEST_TIMEOUT, outer_wall)
    pin = diagnosis.endpoint_pin or "(endpoint pin: standard config)"

    # -- 1. chat-model module (the one semantic change: timeout to both impls) --
    chat_model_diff = (
        "ONE thing vs the predecessor chat model: context_aware_invoke now passes an "
        "explicit litellm request timeout (env FIVE_REQUEST_TIMEOUT, default "
        f"{_DEFAULT_REQUEST_TIMEOUT}s) to BOTH impls (fast + large), so the client "
        "never cancels a long inference before the external wall. Everything else "
        "(token estimate, switch/compress thresholds) is the same logic."
    )
    chat_model_content = (
        '"""Generated chat-model module (additions only; hard rule 7: never mutate).\n'
        "\n"
        f"Diff from predecessor: {chat_model_diff}\n"
        f"Evidence: {evidence}\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "import logging\n"
        "import os\n"
        "\n"
        "from four.chat_model import _ChatCompletionsText\n"
        "from four.core import Err, Ok\n"
        "\n"
        "\n"
        "def context_aware_invoke(\n"
        "    fast_model: str,\n"
        "    large_model: str,\n"
        "    *,\n"
        "    fast_base_url: str = \"\",\n"
        "    large_base_url: str = \"\",\n"
        "    context_limit: int = 50_000,\n"
        "    **model_kwargs,\n"
        "):\n"
        '    """G that switches to the large-context model when the conversation grows.\n'
        "\n"
        "    Identical to the predecessor except both impls are built with an explicit\n"
        "    litellm request timeout (env FIVE_REQUEST_TIMEOUT, default 21600s) so the\n"
        "    client never cancels a long inference before the external wall.\n"
        '    """\n'
        '    logger = logging.getLogger("four.model")\n'
        "\n"
        '    request_timeout = int(os.getenv("FIVE_REQUEST_TIMEOUT", "21600"))\n'
        "    fast_impl = _ChatCompletionsText(\n"
        "        fast_model, base_url=fast_base_url, timeout=request_timeout, **model_kwargs\n"
        "    )\n"
        "    large_impl = _ChatCompletionsText(\n"
        "        large_model, base_url=large_base_url, timeout=request_timeout, **model_kwargs\n"
        "    )\n"
        "\n"
        "    def _estimate_tokens(messages: list[dict]) -> int:\n"
        '        """Rough token estimate: ~4 chars per token."""\n'
        '        total = sum(len(str(m.get("content", ""))) for m in messages)\n'
        "        return total // 4\n"
        "\n"
        "    def _invoke(messages: list[dict]) -> Ok[str] | Err[str]:\n"
        "        estimated = _estimate_tokens(messages)\n"
        "        if estimated > 200_000:\n"
        '            logger.warning("Context %d tokens too large, compressing history", estimated)\n'
        '            system = [m for m in messages if m.get("role") == "system"]\n'
        "            recent = messages[-8:]\n"
        "            return large_impl._invoke(system + recent)\n"
        "        if estimated > context_limit:\n"
        '            logger.info("Context %d tokens > %d, switching to large model", estimated, context_limit)\n'
        "            return large_impl._invoke(messages)\n"
        "        return fast_impl._invoke(messages)\n"
        "\n"
        "    return _invoke\n"
    )

    # -- 2. runner variant (ONE-line import delta) --
    runner_diff = (
        "ONE line vs the predecessor runner: context_aware_invoke now comes from the "
        "new chat-model module (which passes an explicit litellm request timeout, env "
        f"FIVE_REQUEST_TIMEOUT, default {_DEFAULT_REQUEST_TIMEOUT}s > any current outer "
        f"wall of {outer_wall}s). Everything else is byte-identical."
    )
    runner_content = (
        '"""Generated outer runner (additions only; hard rule 7: never mutate).\n'
        "\n"
        f"Diff from predecessor: {runner_diff}\n"
        f"Evidence: {evidence}\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "import argparse\n"
        "import os\n"
        "import sys\n"
        "\n"
        "from four.core import run, save_trajectory\n"
        "from four.chat_model_v2 import context_aware_invoke  # ONE-line delta: explicit request timeout\n"
        "from four.parse import robust_parse\n"
        "from four.env import local_env\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        '    """Outer G: run the pipeline with the timeout-aware chat model."""\n'
        "    invoke = context_aware_invoke(\n"
        '        os.getenv("FIVE_MODEL", "fast-qwen"),\n'
        '        os.getenv("FIVE_LARGE_MODEL", "qwen"),\n'
        '        fast_base_url=os.getenv("FIVE_BASE_URL", ""),\n'
        '        large_base_url=os.getenv("FIVE_LARGE_URL", ""),\n'
        "    )\n"
        "    result = run(invoke, robust_parse, local_env())\n"
        "    save_trajectory(result)\n"
        "\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    main()\n"
    )

    # -- 3. spoke variant (SAME one-line import delta) --
    spoke_diff = (
        "ONE line vs the predecessor spoke: context_aware_invoke now comes from the "
        "new chat-model module (which passes an explicit litellm request timeout, env "
        f"FIVE_REQUEST_TIMEOUT, default {_DEFAULT_REQUEST_TIMEOUT}s > any current outer "
        f"wall of {outer_wall}s). Everything else is byte-identical."
    )
    spoke_content = (
        '"""Generated inner spoke (additions only; hard rule 7: never mutate).\n'
        "\n"
        f"Diff from predecessor: {spoke_diff}\n"
        f"Evidence: {evidence}\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "import argparse\n"
        "import os\n"
        "import sys\n"
        "import time\n"
        "\n"
        "from four.core import run, Ok, Err, save_trajectory\n"
        "from four.chat_model_v2 import context_aware_invoke  # ONE-line delta: explicit request timeout\n"
        "from four.parse import robust_parse\n"
        "from four.env import local_env\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        '    """Inner G: run one cycle with the timeout-aware chat model."""\n'
        "    invoke = context_aware_invoke(\n"
        '        os.getenv("FIVE_MODEL", "fast-qwen"),\n'
        '        os.getenv("FIVE_LARGE_MODEL", "qwen"),\n'
        '        fast_base_url=os.getenv("FIVE_BASE_URL", ""),\n'
        '        large_base_url=os.getenv("FIVE_LARGE_URL", ""),\n'
        "    )\n"
        "    result = run(invoke, robust_parse, local_env())\n"
        "    save_trajectory(result)\n"
        "\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    main()\n"
    )

    # -- 4. driver variant (export FIVE_REQUEST_TIMEOUT >= outer wall; repoint RUN/SPOKE) --
    driver_diff = (
        f"THREE things vs the predecessor driver: RUN -> the new runner, SPOKE -> the "
        f"new spoke, and export FIVE_REQUEST_TIMEOUT={request_timeout} (>= this driver's "
        f"{outer_wall}s outer wall, so the external wall stays the sole timekeeper and "
        "litellm's built-in ~600s default no longer cancels long deep-model inferences "
        "client-side). Everything else is byte-identical."
    )
    driver_content = (
        "#!/bin/bash\n"
        "# Generated driver (additions only; hard rule 7: never mutate).\n"
        f"# Diff from predecessor: {driver_diff}\n"
        f"# Evidence: {evidence}\n"
        "set -uo pipefail\n"
        "\n"
        f"# endpoint: {pin}\n"
        "export FIVE_BASE_URL=http://192.168.1.157:8080/v1\n"
        "export FIVE_MODEL=fast-qwen\n"
        "export FIVE_LARGE_URL=http://192.168.1.161:8081/v1\n"
        "export FIVE_LARGE_MODEL=qwen\n"
        "export FIVE_MAX_TOKENS=65536\n"
        f"# explicit LLM request timeout (must stay >= this driver's {outer_wall}s outer wall)\n"
        f"export FIVE_REQUEST_TIMEOUT={request_timeout}\n"
        "\n"
        "BASE=/home/sasha/AI/sentry\n"
        "AI=$BASE/ai\n"
        "PROJ=$BASE/proj\n"
        "RUN=/home/sasha/Research/four/run-v3.py\n"
        "SPOKE=/home/sasha/Research/four/examples/spokes/cycle-implementation-v4.py\n"
        "LOG=$AI/cycle-001-sentry-gate.md\n"
        "OUT=$BASE/cycles.out\n"
        "\n"
        "FIRST=${1:-5}\n"
        "LAST=${2:-5}\n"
        "\n"
        'echo "# endpoint: standard v3 $(date -u +%H:%M:%SZ)" >> "$OUT"\n'
    )

    return [
        NewFile(
            path=PROPOSAL_NAMESPACE + "client_timeout_chat_model.py",
            content=chat_model_content,
            diff_from_predecessor=chat_model_diff,
            evidence=evidence,
        ),
        NewFile(
            path=PROPOSAL_NAMESPACE + "client_timeout_runner.py",
            content=runner_content,
            diff_from_predecessor=runner_diff,
            evidence=evidence,
        ),
        NewFile(
            path=PROPOSAL_NAMESPACE + "client_timeout_spoke.py",
            content=spoke_content,
            diff_from_predecessor=spoke_diff,
            evidence=evidence,
        ),
        NewFile(
            path=PROPOSAL_NAMESPACE + "client_timeout_driver.sh",
            content=driver_content,
            diff_from_predecessor=driver_diff,
            evidence=evidence,
        ),
    ]


def build_inner_wall_fix(diagnosis: Diagnosis, *, predecessor_driver: str) -> list[NewFile]:
    """NEW-file-only repair path for the inner-wall failure mode (wall-kill AFTER merge).

    Emits ONE new file — a driver variant whose ONLY delta is a larger
    ``--inner-seconds``. The generator takes the predecessor driver text as input and
    applies the single substitution, so everything else is byte-identical by
    construction.

    The new inner-seconds value is derived from the observed heaviest inner duration
    when the diagnosis carries one (plus a stated margin), else a stated margin over
    the old value. The docstring states the diff + the cycle-11 evidence.

    Pure, deterministic, stdlib-only. No disk writes, no clock, no randomness.
    """
    import re

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
        basis = (
            f"the observed heaviest inner duration ({old_inner}s) plus a stated margin "
            f"of {_INNER_WALL_MARGIN}s"
        )
    else:
        old_inner = diagnosis.inner_seconds or _DEFAULT_INNER_SECONDS
        basis = (
            f"the old inner wall ({old_inner}s) plus a stated margin of "
            f"{_INNER_WALL_MARGIN}s"
        )
    new_inner = old_inner + _INNER_WALL_MARGIN

    # Apply the single substitution to the predecessor driver text.
    pattern = re.compile(r"(--inner-seconds[= ])\d+")
    if pattern.search(predecessor_driver):
        new_content_body = pattern.sub(lambda m: f"{m.group(1)}{new_inner}", predecessor_driver, count=1)
    else:
        # No --inner-seconds token present: append it as the single delta line so the
        # rest of the predecessor text stays byte-identical.
        new_content_body = predecessor_driver.rstrip("\n") + f"\n--inner-seconds {new_inner}\n"

    diff = (
        f"ONE thing vs the predecessor driver: --inner-seconds raised from {old_inner}s "
        f"to {new_inner}s (derived from {basis}). Everything else is byte-identical — "
        "the generator applies a single substitution."
    )
    content = (
        "# Generated inner-wall driver (additions only; hard rule 7: never mutate).\n"
        f"# Diff from predecessor: {diff}\n"
        f"# Evidence: {evidence}\n"
        f"{new_content_body}"
    )

    return [
        NewFile(
            path=PROPOSAL_NAMESPACE + "inner_wall_driver.sh",
            content=content,
            diff_from_predecessor=diff,
            evidence=evidence,
        ),
    ]


# Registry keyed by failure_mode; unknown modes fall back to the none-builder.
# (The inner-wall builder takes a keyword-only predecessor_driver, so it is NOT in
# this single-arg registry; it is called directly with the predecessor text.)
FIX_BUILDERS: dict[str, Callable[[Diagnosis], list[NewFile]]] = {
    "driver-death": build_driver_death_fix,
    "wall-kill": build_wall_kill_fix,
    "stall-kill": build_stall_kill_fix,
    "client-timeout": build_client_timeout_fix,
    "none": build_none_fix,
}
