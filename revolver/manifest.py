"""revolver.manifest — the unified, versioned, serializable proposal artifact.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: cycles 3-4 landed the two pure derivations on main — ``propose()``
(revolver/proposal.py) maps a Diagnosis to a NEW-file-only RepairProposal, and
``build_launch_plan()`` (revolver/launch_plan.py) derives a dry-run LaunchPlan
from that proposal. This module unifies them into ONE artifact, the
``ProposalManifest``, that carries the diagnosis, the NEW-file-only repair path,
and the derived launch plan together under a single version stamp. It composes
the two existing pure derivations; it does not re-derive them.

The manifest is DATA ONLY — no process launch, no disk write, no shell. It
exposes a whole-manifest ``validate()`` (the single choke point: a manifest that
passes it is guaranteed additions-only AND launch-safe) and a deterministic
``render()`` to a human-readable text report.

Deterministic, stdlib-only, pure functions with overridable seams.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from revolver.diagnosis import Diagnosis
from revolver.launch_plan import LaunchPlan, build_launch_plan
from revolver.proposal import RepairProposal, propose

if TYPE_CHECKING:
    from collections.abc import Callable

    from revolver.proposal import NewFile

# The manifest schema version (bumped when the to_dict shape changes).
MANIFEST_VERSION = "1.0"


@dataclass
class ProposalManifest:
    """The unified, versioned, serializable proposal artifact.

    Carries the diagnosis, the NEW-file-only repair path, and the derived
    dry-run launch plan together under one version stamp. Data only: no process
    launch, no disk write, no shell.

    Attributes:
        pipeline_id: Which pipeline this manifest belongs to.
        diagnosis: The Diagnosis that motivated the proposal.
        proposal: The NEW-file-only RepairProposal (hard rule 7).
        launch_plan: The derived dry-run LaunchPlan.
        version: The manifest schema version.
    """

    pipeline_id: str
    diagnosis: Diagnosis
    proposal: RepairProposal
    launch_plan: LaunchPlan
    version: str = MANIFEST_VERSION

    # -- round-trip ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless; nested via their own round-trips)."""
        return {
            "pipeline_id": self.pipeline_id,
            "diagnosis": self.diagnosis.to_dict(),
            "proposal": self.proposal.to_dict(),
            "launch_plan": self.launch_plan.to_dict(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProposalManifest:
        """Reconstruct a ProposalManifest from a dict produced by :meth:`to_dict`."""
        return cls(
            pipeline_id=data["pipeline_id"],
            diagnosis=Diagnosis.from_dict(data["diagnosis"]),
            proposal=RepairProposal.from_dict(data["proposal"]),
            launch_plan=LaunchPlan.from_dict(data["launch_plan"]),
            version=data["version"],
        )

    # -- validation ---------------------------------------------------------

    def validate(self, existing_paths: set[str] | None = None) -> ProposalManifest:
        """Re-check every invariant at once; the single choke point.

        Calls the proposal's ``validate()`` (hard rule 7: additions-only) and the
        launch plan's ``validate()`` (launch invariants) so a manifest that passes
        is guaranteed additions-only AND launch-safe.

        Args:
            existing_paths: Optional set of repo-relative paths that already
                exist, forwarded to the proposal's ``validate()``.

        Raises:
            ValueError: naming the first invariant violation (from either the
                proposal or the launch plan).
        """
        self.proposal.validate(existing_paths)
        self.launch_plan.validate()
        return self

    # -- rendering ----------------------------------------------------------

    def render(self) -> str:
        """Render a deterministic, human-readable text report.

        Pure string build — no I/O. Fixed section order; NEW files in stored
        (builder) order. The output is a pure function of the manifest (no
        clock, no randomness, no dict-iteration-order dependence).
        """
        d = self.diagnosis
        plan = self.launch_plan
        lines: list[str] = []
        lines.append(f"=== Proposal Manifest (version {self.version}) ===")
        lines.append(f"pipeline: {self.pipeline_id}")
        lines.append(f"failure_mode: {d.failure_mode}")
        lines.append(f"verdict: {d.verdict}")
        lines.append(f"source: {d.source}")
        lines.append("")
        lines.append("--- REPAIR (new files only) ---")
        if self.proposal.new_files:
            for nf in self.proposal.new_files:
                lines.append(f"+ {nf.path}")
                lines.append(f"    Diff from predecessor: {nf.diff_from_predecessor}")
                lines.append(f"    Evidence: {nf.evidence}")
        else:
            lines.append("(no new files; healthy)")
        lines.append("")
        lines.append("--- LAUNCH (dry-run) ---")
        lines.append(f"command: {plan.command if plan.command else '(none; no-op)'}")
        lines.append(
            f"marker: {plan.cycles_out_append.strip() if plan.cycles_out_append else '(none; no-op)'}"
        )
        lines.append(f"endpoint: {plan.endpoint_pin}")
        lines.append(
            f"request_timeout: {plan.request_timeout}s  outer_wall: {plan.outer_wall}s"
        )
        lines.append(f"one_pipeline_per_endpoint: {plan.one_pipeline_per_endpoint}")
        return "\n".join(lines) + "\n"


def build_manifest(
    diagnosis: Diagnosis,
    *,
    builders: dict[str, Callable[[Diagnosis], list[NewFile]]] | None = None,
) -> ProposalManifest:
    """Compose a Diagnosis into a unified, validated ProposalManifest.

    Composes the two existing pure derivations on main — ``propose(diagnosis)``
    and ``build_launch_plan(proposal)`` — into one artifact. Pure and
    deterministic: the same Diagnosis yields the same manifest (no clock, no
    randomness).

    Args:
        diagnosis: The diagnosis to build a manifest for.
        builders: Overridable registry mapping failure_mode -> fix builder,
            forwarded to ``propose()`` (defaults to ``revolver.fixes.FIX_BUILDERS``).

    Returns:
        A validated ProposalManifest. A healthy diagnosis (failure_mode ==
        "none") yields a manifest with an empty repair path and a no-op launch
        plan.
    """
    proposal = propose(diagnosis, builders=builders)
    launch_plan = build_launch_plan(proposal)
    manifest = ProposalManifest(
        pipeline_id=diagnosis.pipeline_id,
        diagnosis=diagnosis,
        proposal=proposal,
        launch_plan=launch_plan,
        version=MANIFEST_VERSION,
    )
    manifest.validate()
    return manifest
