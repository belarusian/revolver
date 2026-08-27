# TICKET-010: revolver.proposal — NewFile + RepairProposal dataclasses

**Title:** Add `revolver/proposal.py` with a `NewFile` dataclass (path, content,
diff_from_predecessor, evidence) and a `RepairProposal` dataclass (pipeline_id,
diagnosis, new_files, rationale, version) with lossless `to_dict`/`from_dict`.

**Evidence:**
- `revolver/diagnosis.py::Diagnosis` already models the input (failure_mode, evidence,
  endpoint_pin, cycles, verdict, source) and has a proven `to_dict`/`from_dict`
  round-trip + `validate()` pattern to mirror.
- The package docstring (`revolver/__init__.py`) states the house contract: "Every
  generated file is NEW (never mutates an existing one) and carries a docstring
  stating its diff from the predecessor and the evidence motivating it."
- No proposal module exists yet; `diagnose()` produces a `Diagnosis` but nothing turns
  it into a repair path.

**Impact:** There is no typed, versioned container for a repair path; the additive
proposal phase (Build Order cycles 3-5) cannot begin.

**Suggestion:**
- `NewFile(path, content, diff_from_predecessor, evidence)` — a frozen-ish record of one
  NEW file. `content` must embed a docstring: "Diff from predecessor: ..." +
  "Evidence: ...".
- `RepairProposal(pipeline_id, diagnosis, new_files, rationale, version)` — the
  versioned proposal. `to_dict`/`from_dict` lossless (diagnosis nested via its own
  round-trip; new_files as a list of dicts).
- `validate()` enforces hard rule 7: no `new_file.path` may collide with an existing
  repo path (additions only).
