# TICKET-064 — v0.1.0 release (version bump + tag + gh release)

**Cycle:** 13 (Docs + release)
**Target:** `pyproject.toml` + `revolver/__init__.py` + git tag + GitHub release
**Capability:** Bump the version to 0.1.0 in both pyproject.toml and
revolver/__init__.py, commit, tag `v0.1.0`, and create the `v0.1.0` GitHub release
with a short notes body (the 12-cycle build summary from the gate log).

**Acceptance:**
- `pyproject.toml` version == "0.1.0" and `revolver.__version__` == "0.1.0".
- Tag `v0.1.0` exists on the merge commit.
- `gh release create v0.1.0 --notes "..."` succeeds.
- No new runtime code: only README.md, pyproject.toml (version), revolver/__init__.py
  (version), and GitHub metadata change.
