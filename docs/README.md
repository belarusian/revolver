# revolver — documentation

Welcome. revolver is the **hands** of a closed repair loop: sentry (the eyes)
diagnoses a failing pipeline; revolver proposes a minimal, **NEW-file-only**,
versioned repair path; a human approves; the pipeline relaunches on the new path;
and the observer reports whether the diagnosed failure mode recurred.

It is deterministic and stdlib-only. It never mutates an existing file, never
kills a process, and never touches another project's `proj/` repo. Every I/O
boundary is an overridable seam, so the logic is pure and the tests never touch
the real filesystem or spawn a real process.

## Start here

| I want to... | Read |
|--------------|------|
| understand how the pieces fit and *why* they are shaped this way | [ARCHITECTURE.md](ARCHITECTURE.md) — the closed loop (diagnose → propose → approve → deploy → observe) and the seam pattern |
| find a module and see what it depends on | [MODULES.md](MODULES.md) — the catalog of all 14 modules with one-line descriptions and dependency edges |
| look up a function or class signature | [API.md](API.md) — public signatures with type hints, grouped by module |
| run the flow end to end in a few lines | the [Quickstart](../README.md#quickstart) in the root README |

## The loop in one line

```text
diagnose -> propose -> approve -> deploy + relaunch -> observe
```

`diagnose(project_dir)` → `build_manifest(diagnosis)` → human approval →
`deploy_manifest(...)` + `relaunch(...)` → `render_final_report(diagnosis)`.
Each stage hands a typed, versioned artifact to the next.

## The three rules to internalize before you touch code

1. **Additive only (hard rule 7).** Every generated file is NEW and under the
   proposal namespace; nothing is ever mutated.
2. **Human approval gate.** Nothing deploys or relaunches until the approval
   seam returns `True` (the default is `False`).
3. **Seams, not side effects.** All I/O goes through injectable callables; the
   logic stays pure. Add a seam before you add an `open()` or a `subprocess`.

## Where everything lives

- `revolver/` — the 14-module package (see [MODULES.md](MODULES.md)).
- `tests/` — one test file per module plus a replay and smoke suite.
- `tickets/` — the per-cycle work items (this docs tree is TICKET-085).
- `README.md` (repo root) — the narrative guide, quickstart, and design
  invariants. This `docs/` tree splits that single file into a module catalog,
  an API reference, and an architecture document.

## Next steps

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) top to bottom once.
2. Skim [MODULES.md](MODULES.md) so you know where each responsibility lives.
3. Keep [API.md](API.md) open while you work.
4. Return to the [root README](../README.md) for the runnable quickstart.
