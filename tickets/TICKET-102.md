# TICKET-102: `docs/API.md` `Diagnosis` field list missing `inner_wall_driver_path`

Status: DONE
Cycle: 53 (synthesis audit — steady-state maintenance verification)
Parent: TICKET-087

## Evidence

`docs/API.md:35-41` (before fix) listed the `Diagnosis` dataclass fields ending at
`pass_start_max_seq`, with no `inner_wall_driver_path`:

    client_timeout_cycle: int | None
    inner_wall_kill_cycle: int | None
    heaviest_inner_duration: int | None
    outer_wall: int | None
    inner_seconds: int | None
    no_new_trajectory_witnessed: bool
    pass_start_max_seq: int | None

Contradicted by `revolver/diagnosis.py:114` (current):

    inner_wall_driver_path: str | None = None

The field is fully wired: it is a dataclass field (`diagnosis.py:114`), serialized
in `to_dict` (`diagnosis.py:183`), and round-tripped by `from_dict` (which filters
on `cls.__dataclass_fields__`, so every dataclass field is reconstructed). It is
consumed by `build_inner_wall_fix` as the fallback predecessor when
`predecessor_driver` is not passed (`revolver/fixes.py:348-360`; see
`tests/test_fixes_generators.py:409,421`). The field was added by TICKET-087
(commit b098986, "Merge pull request #123 from belarusian/build34/inner-wall-propose").

## Impact
- The API reference omits a public, serialized, round-tripped field of the
  central `Diagnosis` type. A reader reconstructing a `Diagnosis` from the docs
  (or from `to_dict` output) would not know `inner_wall_driver_path` exists, and
  would not know it is the fallback that makes `build_inner_wall_fix` reachable
  via `propose()` with a single argument.
- Steady-state drift: the field is load-bearing for the inner-wall repair path
  but invisible in the API reference.

## Suggestion
Insert `inner_wall_driver_path: str | None` into the `Diagnosis` field list in
`docs/API.md`, in the same position as the code (after `heaviest_inner_duration`,
before `outer_wall`). Docs-only change; no test impact.

## Resolution (Cycle 53)
Inserted `inner_wall_driver_path: str | None` into the `Diagnosis` field list in
`docs/API.md` (now line 38, between `heaviest_inner_duration` and `outer_wall`),
matching the code order at `revolver/diagnosis.py:114`. Verified the field is
present in `to_dict` (`diagnosis.py:183`) and round-tripped by `from_dict`.
Docs-only change; gate re-measured green (415 passed / ruff clean / mypy clean,
14 files).
