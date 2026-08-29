"""revolver.triple — the pinned derivation baseline, carried by REFERENCE only.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: Build Order row "Derive-by-reference | 17-19" + TICKET-075. The law this
module encodes: artifacts carry REFERENCES (paths + checksums), never VALUES. The
three seed elements of the golden v3 set are pinned by sha256 against the Sunny
execution plane (~/Research/four main @ 26d0317) and physically held in the META
dir (~/AI/revolver/triple/), which is OUTSIDE the artifact repo. This module
therefore contains NO file bodies, NO embedded content — only the meta-dir path,
the pinned checksums, and the verify/resolve functions that read the files at
resolve time and fail loud on any checksum mismatch.

The physical copies are made with `cp` on the execution plane (never `git mv`,
never into the artifact tree). The artifact never receives meta code by value.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# The META dir: the ONLY physical landing site for the pinned seed triple. It is
# deliberately OUTSIDE the artifact repo (mediator override 2026-08-28).
TRIPLE_DIR = Path("/home/sasha/AI/revolver/triple")

# The execution-plane provenance the checksums are pinned against (reference only —
# a path + a commit sha, never the tree contents).
SEED_REPO = Path("/home/sasha/Research/four")
SEED_COMMIT = "26d031781658674cd5367bd6cea569f8d5c60f2a"

# The pinned triple: name -> (sha256, source path on the execution plane). The
# sha256 values are the 2026-08-28 Sunny-plane digests (see the Build Order row).
# Only names + hashes live here — never the file contents.
TRIPLE: dict[str, tuple[str, Path]] = {
    "run-v3.py": (
        "fb89fa8e42e30b8130f1d65f31e3f374031654a35f0e6091c41a5c4ddf60f510",
        SEED_REPO / "run-v3.py",
    ),
    "cycle-implementation-v4.py": (
        "9672f5d5cbdef58aa205b0637331d0ed9de5a2387d47edff34324f9bb79ab8dc",
        SEED_REPO / "examples" / "spokes" / "cycle-implementation-v4.py",
    ),
    "run-cycles-v3.sh": (
        "5997f3caa51f49836317b3d00e7dee116bdff0463543c490bd6939f6de7d55bf",
        Path("/home/sasha/AI/sentry/run-cycles-v3.sh"),
    ),
}


class TripleMismatch(Exception):
    """Raised when a meta-dir file's sha256 does not match the pinned checksum.

    The derivation baseline is corrupt or has drifted from the pinned seed; the
    proposal must fail loud rather than derive over an unpinned predecessor.
    """


def _sha256(path: Path) -> str:
    """Return the sha256 hex digest of a file (read-only, stdlib only)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_triple(triple_dir: Path | None = None) -> None:
    """Verify every pinned triple element against its sha256.

    Reads each file at ``triple_dir`` (default :data:`TRIPLE_DIR`) and compares its
    sha256 to the pinned checksum. Raises :class:`TripleMismatch` naming the first
    element whose digest does not match (or that is missing). Pure read-only: no
    write, no process launch.
    """
    base = triple_dir if triple_dir is not None else TRIPLE_DIR
    for name, (expected, _source) in TRIPLE.items():
        path = base / name
        if not path.is_file():
            raise TripleMismatch(f"triple element missing: {path}")
        actual = _sha256(path)
        if actual != expected:
            raise TripleMismatch(
                f"triple checksum mismatch for {name}: "
                f"expected {expected}, got {actual}"
            )


def resolve(name: str, triple_dir: Path | None = None) -> Path:
    """Return the meta-dir path for a triple element, verifying it first.

    ``name`` must be one of the pinned triple elements. The whole triple is
    verified (fail loud on any mismatch) before the path is returned, so a
    caller can never derive over an unpinned predecessor. Raises
    :class:`TripleMismatch` on a bad checksum or a missing element, and
    ``KeyError`` for an unknown name.
    """
    if name not in TRIPLE:
        raise KeyError(f"unknown triple element: {name!r}")
    verify_triple(triple_dir)
    base = triple_dir if triple_dir is not None else TRIPLE_DIR
    return base / name
