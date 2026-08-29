# TICKET-075 — Seed-triple pin: meta-dir copies + sha256 verification (references, not values)

**Status:** TODO
**Cycle:** 17
**Build Order row:** Derive-by-reference (17–19)

## Capability
Establish the pinned derivation baseline WITHOUT placing meta code in the artifact:
- In the META repo (NOT the artifact repo): create `~/AI/revolver/triple/` holding
  copies of the three seed elements — `run-v3.py`, `cycle-implementation-v4.py`,
  `run-cycles-v3.sh` — each with a sibling `.sha256` file. The physical copies live on
  the execution plane only (mediator override 2026-08-28: the artifact must never carry
  a by-value copy of meta components; the artifact carries REFERENCES — paths +
  checksums — never contents).
- In the artifact: `revolver/triple.py` — a REFERENCES-ONLY module: constants
  `TRIPLE_DIR = Path("/home/sasha/AI/revolver/triple")` and the pinned checksums
  (`run-v3.py fb89fa8e…`, `cycle-implementation-v4.py 9672f5d5…`,
  `run-cycles-v3.sh 5997f3ca…`, execution plane `~/Research/four` main @ 26d0317),
  plus `verify_triple() -> None` (reads files at resolve time, sha256-compares, raises
  on mismatch) and `resolve(name) -> Path` (returns the meta-dir path; verifies first).
  No file bodies, no embedded content — the module is paths and hashes only.

## Acceptance
- `revolver/triple.py` contains no code from the seed files (grep: no `import litellm`,
  no `run(`, no driver `export` lines — names and hashes only).
- `verify_triple()` passes on the execution plane; raises `TripleMismatch` when a
  checksum is wrong (test with monkeypatched sha256 or a temp dir + wrong hash).
- `resolve("run-v3.py")` returns the meta-dir path after verification.
- The meta-dir triple is created with `cp` (never git mv, never in the artifact tree);
  `sha256sum` output committed inside `triple/*.sha256`.
