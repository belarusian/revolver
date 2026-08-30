# revolver — architecture

revolver is the **hands** of a closed repair loop. sentry (the eyes) diagnoses a
failing pipeline; revolver proposes a minimal, NEW-file-only, versioned repair
path; a human approves; the pipeline relaunches on the new path; and the observer
reports whether the diagnosed failure mode recurred.

The whole design is shaped by three constraints:

1. **Deterministic + stdlib-only.** No clock, no randomness, no third-party
   runtime dependency. The same input always yields the same output.
2. **Additive only (hard rule 7).** revolver never mutates an existing file.
   Every generated path is NEW and lives under the proposal namespace.
3. **Every I/O boundary is a seam.** The logic is pure; the side effects live
   behind injectable callables. See [The seam pattern](#the-seam-pattern).

## The closed loop

Five stages, each owned by a module, each passing a typed, versioned artifact to
the next:

```text
   diagnose  ->  propose  ->  approve  ->  deploy + relaunch  ->  observe
      |            |            |               |                    |
   Diagnosis   ProposalManifest  (human)     DeployReport /      FinalReport
      |            |                          LaunchReport            |
      +------------+---------------------------------------------------+
                              (the loop closes: observe feeds the next diagnose)
```

### 1. Diagnose — `revolver.diagnosis`

`diagnose(project_dir)` turns a project directory into a typed, versioned
`Diagnosis`. It tries the pinned sentry check runner first (via
`revolver.sentry_client`); when sentry is not importable it degrades to raw-artifact
parsing (`cycles.out` markers, gate-log cycle blocks, the newest trajectory
outcome) and records `source="raw-artifacts"` so provenance is never lost. The
house exit-code convention is 0 = healthy, 1 = action needed, 2 = usage error.

The `Diagnosis` carries a coarse `failure_mode` tag (`driver-death`, `wall-kill`,
`stall-kill`, `client-timeout`, `inner-wall`, `outer-freshness`, or `none`) that
drives the next stage.

### 2. Propose — `revolver.manifest` (composing `proposal` + `launch_plan`)

`build_manifest(diagnosis)` composes two pure derivations into one validated
`ProposalManifest`:

- `propose(diagnosis)` (`revolver.proposal`) maps the `failure_mode` to a minimal
  NEW-file-only repair path via the `FIX_BUILDERS` registry (`revolver.fixes`).
  A healthy diagnosis yields an empty repair path.
- `build_launch_plan(proposal)` (`revolver.launch_plan`) derives a dry-run
  `LaunchPlan`: the command line, the `cycles.out` marker to append, the endpoint
  pin (verbatim), and the two wall-clock budgets.

`ProposalManifest.validate()` is the **single choke point**: a manifest that
passes it is guaranteed additions-only AND launch-safe. `render()` produces a
deterministic text report.

### 3. Approve — the human gate

Nothing is deployed or relaunched until the approval seam returns `True`. The
default approval seam (`revolver.deploy`) always returns `False`, so the safe
default is "do nothing." The `plan` (propose) / `apply` (deploy) split *is* the
gate.

### 4. Deploy + relaunch — `revolver.deploy` (planning: `revolver.relaunch`)

On approval, `deploy_manifest(manifest, base_dir=..., approved=...)` writes the
NEW files (additions-only; an existing target path is skipped and an error is
recorded — hard rule 7). `relaunch(manifest)` executes the launch-plan command.
**No process is killed** — killing a hung PID stays sentry's job.

`revolver.relaunch` adds the planning/verification layer: `first_not_done_cycle`
(the resume point), `plan_relaunch` (a resume-aware command scoped to the first
not-done cycle), and `verify_relaunch` (marker present in `cycles.out` AND driver
alive).

### 5. Observe — `revolver.observe`

`render_final_report(diagnosis)` composes three read-only observations into a
single `FinalReport` stating whether the diagnosed failure mode recurred:

- the `cycles.out` marker observation (done / in-flight / gaps);
- the per-cycle trajectory outcomes;
- the git merge-commit observation (merged / missing).

The observer reports honestly: a cycle with no marker is a *gap*, never assumed
done; a cycle with no merge commit is *missing*, never assumed merged (the §7
union rule). `render(report)` renders the report as deterministic text.

## The seam pattern

Every module that could touch the outside world does so through an **overridable
seam** — a `Callable` parameter that defaults to the real side effect but can be
replaced with a fake. This is the sentry pattern: injectable I/O so the logic is
pure and the tests never touch the real filesystem or spawn a real process.

```text
   pure logic  --(seam: Callable)-->  default: real I/O
        |                              (read_file, write_file, run_command,
        +-- tests inject a fake         read_cycles_out, read_trajectory,
            (no fs, no process)         read_git_log, approved, driver_alive)
```

Representative seams:

| Seam | Module | Default side effect |
|------|--------|---------------------|
| `read_file` | `diagnosis` | `Path.read_text` |
| `run_check` (method) | `sentry_client` | import + call `sentry.cli.main` |
| `read_text`, `compile_check` | `derive` | real file read; `py_compile` on a temp file |
| `write_file`, `approved` | `deploy` | real `open(..., 'w')`; always `False` |
| `run_command` | `deploy` | `subprocess.run(shell=True)` |
| `read_cycles_out`, `driver_alive` | `relaunch` | read `cycles.out`; scan `/proc` |
| `read_cycles_out`, `read_trajectory`, `read_git_log` | `observe` | read `cycles.out`, newest trajectory, `.git/logs/HEAD` |

Because the seams are the only I/O, the same functions run unchanged in tests
(with fakes) and in production (with the defaults). The default seams are the
*only* place a real file is read or a real process is launched.

## References, not values (derive-by-reference)

Two modules encode the law that **artifacts carry REFERENCES (paths + checksums),
never VALUES**:

- `revolver.triple` pins the three seed elements of the golden v3 set by sha256
  against the execution plane and holds them physically in the META dir
  (outside the artifact repo). It contains no file bodies — only the meta-dir
  path, the pinned checksums, and `verify_triple`/`resolve` that fail loud on any
  checksum mismatch.
- `revolver.derive` reads a predecessor READ-ONLY, applies EXACTLY ONE stated
  minimal edit, and emits a NEW versioned file whose docstring names the
  predecessor by PATH (the version chain). Verification is by construction and
  fails loud: the output must compile and differ from the predecessor by exactly
  the stated lines; any extra delta is a `DerivationError`.

The fix builders in `revolver.fixes` are thin instruction emitters over
`derive()`: they compose `ChangeInstruction` objects and resolve predecessors by
PATH from the triple meta dir. No module body is ever embedded as text.

## Design invariants

- **Additive files only (hard rule 7).** Every generated path is NEW and under
  the proposal namespace; `validate()` and the deploy step both reject an
  existing-path collision.
- **Human approval gate.** Nothing deploys or relaunches until the approval seam
  returns `True`.
- **Never kills processes.** Killing a hung PID stays sentry's job.
- **Never touches other projects' `proj/` repos.** revolver operates on the
  diagnosed project's artifacts through its seams.
- **Never changes endpoint allocation.** The endpoint pin is carried verbatim;
  one pipeline per endpoint is an enforced invariant.
- **Deterministic + stdlib-only, with overridable I/O seams.**

## Where to go next

- Module catalog + dependency edges: [MODULES.md](MODULES.md)
- Public signatures with type hints: [API.md](API.md)
- Newcomer landing page: [README.md](README.md)
- Narrative quickstart + invariants: [../README.md](../README.md)
