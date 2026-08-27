"""revolver.proposal — NEW-file-only repair-path generator core.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: the package contract (revolver/__init__.py) states that every generated
file is NEW (never mutates an existing one) and carries a docstring stating its
diff from the predecessor and the evidence motivating it. This module defines the
typed, versioned containers (``NewFile``, ``RepairProposal``) and the ``propose()``
entry point that maps a ``Diagnosis.failure_mode`` to a minimal NEW-file-only
repair path.

Deterministic, stdlib-only, pure functions with overridable seams. Nothing here
writes to disk or launches a process: deployment/relaunch is a later phase
(cycles 8-9), validation is cycles 6-7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from revolver.diagnosis import Diagnosis

if TYPE_CHECKING:
    from collections.abc import Callable

# The proposal schema version (bumped when the to_dict shape changes).
PROPOSAL_VERSION = "1.0"

# The proposal-owned namespace: every generated path lives under this prefix so the
# repair path is additions-only (hard rule 7: never mutate an existing file).
PROPOSAL_NAMESPACE = "revolver/fixes/"


@dataclass
class NewFile:
    """One NEW file in a repair path (additions only — never a mutation).

    Attributes:
        path: Relative path of the file to add (always under PROPOSAL_NAMESPACE).
        content: The file's text. Must embed a docstring stating
            "Diff from predecessor: ..." and "Evidence: ...".
        diff_from_predecessor: The diff-from-predecessor statement.
        evidence: The motivating evidence.
    """

    path: str
    content: str
    diff_from_predecessor: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless)."""
        return {
            "path": self.path,
            "content": self.content,
            "diff_from_predecessor": self.diff_from_predecessor,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewFile:
        """Reconstruct a NewFile from a dict produced by :meth:`to_dict`."""
        return cls(
            path=data["path"],
            content=data["content"],
            diff_from_predecessor=data["diff_from_predecessor"],
            evidence=data["evidence"],
        )


@dataclass
class RepairProposal:
    """A typed, versioned, NEW-file-only repair path for a Diagnosis.

    Attributes:
        pipeline_id: Which pipeline this proposal belongs to.
        diagnosis: The Diagnosis that motivated the proposal.
        new_files: The NEW files to add (never a mutation of an existing path).
        rationale: Free-text rationale for the repair path.
        version: The proposal schema version.
    """

    pipeline_id: str
    diagnosis: Diagnosis
    new_files: list[NewFile] = field(default_factory=list)
    rationale: str = ""
    version: str = PROPOSAL_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (lossless; diagnosis nested via its own round-trip)."""
        return {
            "pipeline_id": self.pipeline_id,
            "diagnosis": self.diagnosis.to_dict(),
            "new_files": [nf.to_dict() for nf in self.new_files],
            "rationale": self.rationale,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairProposal:
        """Reconstruct a RepairProposal from a dict produced by :meth:`to_dict`."""
        return cls(
            pipeline_id=data["pipeline_id"],
            diagnosis=Diagnosis.from_dict(data["diagnosis"]),
            new_files=[NewFile.from_dict(nf) for nf in data["new_files"]],
            rationale=data["rationale"],
            version=data["version"],
        )

    def validate(self, existing_paths: set[str] | None = None) -> RepairProposal:
        """Enforce hard rule 7: additions only, never a mutation of an existing path.

        Args:
            existing_paths: Optional set of repo-relative paths that already exist.
                If given, any ``new_file.path`` in this set is a mutation and is
                rejected.

        Raises:
            ValueError: if a ``new_file.path`` is not under PROPOSAL_NAMESPACE, or
                collides with an existing path.
        """
        existing = existing_paths or set()
        for nf in self.new_files:
            if not nf.path.startswith(PROPOSAL_NAMESPACE):
                raise ValueError(
                    f"hard rule 7 violated: {nf.path!r} is not an addition under "
                    f"{PROPOSAL_NAMESPACE!r}"
                )
            if nf.path in existing:
                raise ValueError(
                    f"hard rule 7 violated: {nf.path!r} already exists (mutation)"
                )
        return self


def propose(
    diagnosis: Diagnosis,
    *,
    builders: dict[str, Callable[[Diagnosis], list[NewFile]]] | None = None,
) -> RepairProposal:
    """Map a Diagnosis to a minimal NEW-file-only repair path.

    Args:
        diagnosis: The diagnosis to repair.
        builders: Overridable registry mapping failure_mode -> fix builder (the
            sentry pattern: injectable so tests never depend on the concrete
            builders). Defaults to ``revolver.fixes.FIX_BUILDERS``.

    Returns:
        A validated RepairProposal. A healthy diagnosis (failure_mode == "none")
        yields an empty ``new_files`` list (no-op proposal).
    """
    if builders is None:
        from revolver.fixes import FIX_BUILDERS

        builders = FIX_BUILDERS

    builder = builders.get(diagnosis.failure_mode, builders.get("none"))
    new_files: list[NewFile] = builder(diagnosis) if builder is not None else []

    if diagnosis.failure_mode == "none":
        rationale = "no action needed (healthy); empty repair path"
    else:
        rationale = (
            f"repair path for failure_mode={diagnosis.failure_mode!r}: "
            f"{len(new_files)} new file(s), additions only (hard rule 7)."
        )

    proposal = RepairProposal(
        pipeline_id=diagnosis.pipeline_id,
        diagnosis=diagnosis,
        new_files=new_files,
        rationale=rationale,
        version=PROPOSAL_VERSION,
    )
    proposal.validate()
    return proposal
