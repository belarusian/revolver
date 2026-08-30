# revolver

**The hands of the closed loop.** sentry (the eyes) diagnoses a failing pipeline;
revolver proposes a minimal **NEW-file-only**, versioned repair path; a human approves;
the pipeline relaunches on the new path; and the observer reports whether the diagnosed
failure mode recurred.

revolver is deterministic and stdlib-only. It never mutates an existing file, never
kills a process, and never touches another project's `proj/` repo. Every I/O boundary
is an overridable seam, so the logic is pure and the tests never touch the real
filesystem or spawn a real process.

## The closed loop

1. **Diagnose** - `diagnose(project_dir)` parses a sentry check/rescue report (or, when
   sentry is not importable, the raw artifacts: `cycles.out` markers, gate-log cycle
   blocks, the newest trajectory outcome) into a typed, versioned `Diagnosis`.
2. **Propose** - `build_manifest(diagnosis)` composes a NEW-file-only `RepairProposal`
   and a dry-run `LaunchPlan` into one validated `ProposalManifest`.
3. **Approve** - a human approves. `deploy_manifest(..., approved=...)` writes nothing
   unless the approval seam returns True.
4. **Deploy + relaunch** - on approval, `deploy_manifest` writes the NEW files
   (additions-only) and `relaunch` executes the launch-plan command. No process is
   killed - killing stays sentry's job.
5. **Observe + report** - `render_final_report(diagnosis)` composes the marker,
   trajectory, and git observations into a single report stating whether the diagnosed
   failure mode recurred.

## Quickstart

There is **no CLI entry point** - revolver is a library. The `revolver plan` /
`revolver apply` / `revolver launch` strings that appear in a launch-plan command are
*generated text* (the command the deployed pipeline would run), not revolver commands.
The flow is driven by the public functions below.

```python
from pathlib import Path
from revolver.diagnosis import diagnose
from revolver.manifest import build_manifest
from revolver.deploy import deploy_manifest, relaunch
from revolver.observe import render_final_report, render

# 1. Diagnose a project directory (sentry first, raw-artifacts fallback).
diagnosis = diagnose(Path("/path/to/project"))

# 2. Propose: a validated, NEW-file-only ProposalManifest.
manifest = build_manifest(diagnosis)
print(manifest.render())          # deterministic human-readable text report

# 3. Approve + deploy (additions-only; writes nothing unless approved).
report = deploy_manifest(
    manifest,
    base_dir=Path("/path/to/project"),
    approved=lambda: True,        # the human-approval gate
)

# 4. Relaunch the pipeline on the new path (no process kill).
launch = relaunch(manifest)

# 5. Observe + report whether the diagnosed failure mode recurred.
final = render_final_report(diagnosis)
print(render(final))
```

All I/O is behind overridable seams (`read_file`, `write_file`, `run_command`,
`read_cycles_out`, `read_trajectory`, `read_git_log`, ...). Inject fakes to test the
logic without touching the real filesystem or spawning a process.

## Modules

One row per module in `revolver/`, mirroring each module's docstring.

| Module | Role |
|---|---|
| `diagnosis.py` | Parse a sentry check/rescue diagnosis into a typed, versioned `Diagnosis`. Tries sentry first; degrades to raw-artifact parsing (cycles.out markers, gate-log blocks, newest trajectory outcome) and records the provenance. House exit-code convention: 0 healthy, 1 action needed, 2 usage error. |
| `sentry_client.py` | Invoke `sentry check` via the pinned dependency behind an overridable runner seam; map the house exit code onto the record. Raises `ImportError` when sentry is not importable so the caller can degrade. |
| `sentry_pin.py` | Resolve sentry as a pinned git dependency (loop-doctor pattern: `name @ git+https://...git@<full-sha>`). Pure: parses, renders, and validates the pin requirement string; no git I/O. |
| `proposal.py` | NEW-file-only repair-path generator core. `NewFile` + `RepairProposal` containers and the `propose()` entry point that maps a `Diagnosis.failure_mode` to a minimal NEW-file-only path. `validate()` enforces hard rule 7 (every path under the proposal namespace, no collision with an existing path). |
| `fixes.py` | Concrete per-failure-mode fix builders (`build_driver_death_fix`, `build_wall_kill_fix`, `build_stall_kill_fix`, `build_none_fix`) + the `FIX_BUILDERS` registry. Each actionable builder emits a plan file PLUS a `cycles.out` marker file; the healthy builder emits an empty path. |
| `manifest.py` | The unified, versioned, serializable `ProposalManifest` (diagnosis + NEW-file-only repair path + derived launch plan under one version stamp). Composes `propose()` + `build_launch_plan()`; exposes a whole-manifest `validate()` (the single choke point) and a deterministic `render()`. |
| `launch_plan.py` | Deterministic dry-run launch-plan derivation: the command line, the cycles.out marker to append, the endpoint pin (verbatim), and the two wall-clock budgets. Enforces one pipeline per endpoint and `request_timeout >= outer_wall`. No disk write, no process launch. |
| `validation.py` | Pure, dry-run validation of proposal artifacts: static Python-syntax + import checks on each NEW file's content, and command-shape checks on the launch plan (nohup, append-not-truncate marker, verbatim endpoint pin, `request_timeout >= outer_wall`, one pipeline per endpoint). No I/O, no process launch. |
| `deploy.py` | Deployment + relaunch execution for a validated `ProposalManifest`. `deploy_manifest` writes the NEW files (additions-only, hard rule 7) on human approval; `relaunch` executes the launch-plan command. Both gated behind overridable seams. No process kill. |
| `relaunch.py` | Deterministic relaunch planning + verification: `first_not_done_cycle` (the resume point), `plan_relaunch` (a resume-aware command scoped to the first not-done cycle), and `verify_relaunch` (marker in cycles.out + driver alive). No process kill. |
| `observe.py` | The read-only observer half of the loop. Parses `cycles.out` into per-cycle markers (file order, never reordered/deduped), the per-cycle trajectory outcomes, and the git merge commits; reports done / in-flight / gaps honestly and composes them into a recurrence verdict (`report`) and a final report (`render_final_report` / `render`). Read-only: no launch, no kill, no write. |
| `derive.py` | Derive-by-reference: predecessor-in, versioned-variant-out. The core of the derive-by-reference procedure that replaces value-embedding generators: read a predecessor READ-ONLY, apply EXACTLY ONE stated minimal edit, and emit a NEW versioned file whose docstring names the predecessor by PATH (the version chain). Verification is by construction and fails loud: the output must compile and differ from the predecessor by exactly the stated lines; any extra delta is a `DerivationError`. Pure, stdlib-only, overridable I/O seams. |
| `triple.py` | The pinned derivation baseline, carried by REFERENCE only. Encodes the law that artifacts carry REFERENCES (paths + checksums), never VALUES: the three seed elements of the golden v3 set are pinned by sha256 against the Sunny execution plane and physically held in the META dir (outside the artifact repo). Contains NO file bodies or embedded content — only the meta-dir path, the pinned checksums, and verify/resolve functions that read the files at resolve time and fail loud on any checksum mismatch. |

## Design invariants

- **Additive files only (hard rule 7).** revolver never mutates an existing file. Every
  generated path is NEW and under the proposal namespace; `validate()` and the deploy
  step both reject an existing-path collision.
- **Human approval gate.** Nothing is deployed or relaunched until the approval seam
  returns True. The `plan` (propose) / `apply` (deploy) split is the gate.
- **Never kills processes.** Killing a hung PID stays sentry's job. revolver only
  proposes, deploys, and relaunches.
- **Never touches other projects' `proj/` repos.** revolver operates on the diagnosed
  project's artifacts through its seams; it does not reach into sibling repos.
- **Never changes endpoint allocation.** The endpoint pin is carried verbatim; one
  pipeline per endpoint is an enforced invariant.
- **Deterministic + stdlib-only, with overridable I/O seams.** No clock, no randomness,
  no third-party runtime dependency. Every I/O boundary is an injectable seam so the
  logic is pure and testable.

## Acceptance criteria

The build was tested against the two founding fix classes - the failure modes the
pipeline actually hit and that the fix builders must repair:

- **The client-timeout class** (a per-request budget that undercuts the outer wall):
  the launch plan enforces `request_timeout >= outer_wall`, and `check_launch_plan`
  rejects a plan that violates it.
- **The inner-wall class** (a cycle wall-killed without merging, or a hung inner PID):
  the `wall-kill` and `stall-kill` fix builders emit a minimal NEW-file-only repair
  path, and the observer's recurrence verdict reports whether the mode recurred after
  the relaunch.

## Version

`0.2.0` - the Build Order build (cycles 1-24: diagnosis intake, additive proposal, proposal
validation, deploy + relaunch, observe + report) is complete. See the gate log
(`ai/cycle-001-revolver-gate.md`) for the per-cycle record.
