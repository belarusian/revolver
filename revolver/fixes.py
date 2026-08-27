"""revolver.fixes — concrete per-failure-mode fix builders.

Diff from predecessor: NEW module (no predecessor in this repo).
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

# The generated-file path for a given failure mode (always under the proposal
# namespace so the repair path is additions-only).
_PATHS = {
    "driver-death": PROPOSAL_NAMESPACE + "driver_death_relaunch.py",
    "wall-kill": PROPOSAL_NAMESPACE + "wall_kill_remerge.py",
    "stall-kill": PROPOSAL_NAMESPACE + "stall_inner_kill.py",
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


def build_driver_death_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for a dead driver process.

    Pure, deterministic, stdlib-only. Emits a relaunch-plan file (no process is
    actually launched here — that is cycles 8-9).
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
    return [
        NewFile(
            path=_PATHS["driver-death"],
            content=_content(diff, evidence, body),
            diff_from_predecessor=diff,
            evidence=evidence,
        )
    ]


def build_wall_kill_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for a wall-killed cycle that never merged.

    Pure, deterministic, stdlib-only. Emits a remerge-plan file.
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
    return [
        NewFile(
            path=_PATHS["wall-kill"],
            content=_content(diff, evidence, body),
            diff_from_predecessor=diff,
            evidence=evidence,
        )
    ]


def build_stall_kill_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """NEW-file-only repair path for a stalled inner PID.

    Pure, deterministic, stdlib-only. Emits an inner-PID kill-plan file (kill the
    inner PID only, NEVER the driver — that stays sentry's).
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
    return [
        NewFile(
            path=_PATHS["stall-kill"],
            content=_content(diff, evidence, body),
            diff_from_predecessor=diff,
            evidence=evidence,
        )
    ]


def build_none_fix(diagnosis: Diagnosis) -> list[NewFile]:
    """Healthy diagnosis -> empty repair path (no-op proposal)."""
    return []


# Registry keyed by failure_mode; unknown modes fall back to the none-builder.
FIX_BUILDERS: dict[str, Callable[[Diagnosis], list[NewFile]]] = {
    "driver-death": build_driver_death_fix,
    "wall-kill": build_wall_kill_fix,
    "stall-kill": build_stall_kill_fix,
    "none": build_none_fix,
}
