"""tests/test_triple.py — seed-triple pin: references-not-values acceptance.

Diff from predecessor: NEW test module (no predecessor in this repo).
Evidence: TICKET-075. The artifact carries REFERENCES (paths + checksums), never
VALUES. These tests assert (a) the module contains no seed code, (b) verify_triple
passes on the execution plane (skip-guarded for the GitHub lens), (c) verify_triple
raises TripleMismatch on a wrong checksum, and (d) resolve returns the meta-dir
path after verification.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from revolver import triple
from revolver.triple import TRIPLE, TRIPLE_DIR, TripleMismatch, resolve, verify_triple

# The module source, read once for the "no seed code" acceptance check.
_MODULE_SRC = (Path(triple.__file__)).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestReferencesNotValues:
    def test_module_contains_no_seed_code(self):
        # Acceptance: no litellm import, no run( call, no driver export lines,
        # no chat-model body — names and hashes only.
        assert "import litellm" not in _MODULE_SRC
        assert "context_aware_invoke" not in _MODULE_SRC
        assert "export FIVE" not in _MODULE_SRC
        assert "def main" not in _MODULE_SRC
        # The only "run" tokens are the triple element filenames, not a run() call.
        assert not re.search(r"\brun\(", _MODULE_SRC)

    def test_triple_pins_names_and_hashes_only(self):
        # Every pinned element maps to (sha256, source path) — a reference pair.
        assert set(TRIPLE) == {
            "run-v3.py",
            "cycle-implementation-v4.py",
            "run-cycles-v3.sh",
        }
        for name, (digest, source) in TRIPLE.items():
            assert re.fullmatch(r"[0-9a-f]{64}", digest), name
            assert isinstance(source, Path), name

    def test_triple_dir_is_outside_the_artifact(self):
        # The meta dir is the only physical landing site and is NOT in the repo.
        assert TRIPLE_DIR == Path("/home/sasha/AI/revolver/triple")
        assert "revolver/proj" not in str(TRIPLE_DIR)


class TestVerifyTriple:
    def test_verify_passes_on_execution_plane(self, tmp_path: Path):
        # Build a faithful temp triple from the pinned digests (skip off-plane).
        if not all(src.is_file() for _d, src in TRIPLE.values()):
            pytest.skip("seed triple not present on this plane (GitHub lens)")
        for name, (_digest, source) in TRIPLE.items():
            (tmp_path / name).write_bytes(source.read_bytes())
        verify_triple(tmp_path)  # must not raise

    def test_verify_raises_on_wrong_checksum(self, tmp_path: Path):
        # A temp triple with one corrupted element must fail loud.
        for name, (_digest, source) in TRIPLE.items():
            data = source.read_bytes() if source.is_file() else b"stub"
            (tmp_path / name).write_bytes(data)
        # Corrupt run-v3.py so its digest no longer matches the pin.
        (tmp_path / "run-v3.py").write_bytes(b"corrupted content\n")
        with pytest.raises(TripleMismatch, match="run-v3.py"):
            verify_triple(tmp_path)

    def test_verify_raises_on_missing_element(self, tmp_path: Path):
        # A missing element is a mismatch (the baseline is incomplete). Fully
        # self-contained (no execution-plane reads): leave the FIRST pinned
        # element absent and stub the rest, so verify_triple hits the missing
        # element before any checksum comparison. Deterministic on every plane.
        first = next(iter(TRIPLE))
        for name in TRIPLE:
            if name != first:
                (tmp_path / name).write_bytes(b"stub")
        with pytest.raises(TripleMismatch, match="missing"):
            verify_triple(tmp_path)

    def test_verify_default_dir_on_execution_plane(self):
        # The default TRIPLE_DIR verifies on the execution plane (skip off-plane).
        if not TRIPLE_DIR.is_dir():
            pytest.skip("meta triple dir not present on this plane (GitHub lens)")
        verify_triple()  # must not raise


class TestResolve:
    def test_resolve_returns_meta_dir_path(self, tmp_path: Path):
        for name, (_digest, source) in TRIPLE.items():
            data = source.read_bytes() if source.is_file() else b"stub"
            (tmp_path / name).write_bytes(data)
        path = resolve("run-v3.py", triple_dir=tmp_path)
        assert path == tmp_path / "run-v3.py"
        assert path.is_file()

    def test_resolve_verifies_before_returning(self, tmp_path: Path):
        # resolve must fail loud if the triple is corrupt (verify-first).
        for name, (_digest, source) in TRIPLE.items():
            data = source.read_bytes() if source.is_file() else b"stub"
            (tmp_path / name).write_bytes(data)
        (tmp_path / "cycle-implementation-v4.py").write_bytes(b"corrupt\n")
        with pytest.raises(TripleMismatch):
            resolve("run-v3.py", triple_dir=tmp_path)

    def test_resolve_unknown_name_raises(self, tmp_path: Path):
        with pytest.raises(KeyError):
            resolve("not-a-triple-element.py", triple_dir=tmp_path)
