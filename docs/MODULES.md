# revolver — module catalog

Catalog of all 14 modules in `revolver/`, one line each, plus the dependency
edges between them. This is the machine-readable module map that the single
`README.md` used to carry inline.

The package is **deterministic, stdlib-only, and pure**: every module exposes
overridable I/O seams so the logic never touches the real filesystem or spawns a
process. No module imports another project's `proj/` repo.

## Modules

| # | Module | One-line description |
|---|--------|----------------------|
| 1 | `revolver/__init__.py` | Package root; declares the contract (NEW-file-only, versioned repair paths) and `__version__`. |
| 2 | `revolver/diagnosis.py` | Parses a sentry check/rescue report (or raw artifacts) into a typed, versioned `Diagnosis`; house exit codes 0/1/2. |
| 3 | `revolver/sentry_client.py` | Invokes `sentry check` behind an overridable runner seam and maps the house exit code onto the record; raises `ImportError` when sentry is absent. |
| 4 | `revolver/sentry_pin.py` | Resolves sentry as a pinned git dependency (`name @ git+https://...git@<full-sha>`); parses, renders, and validates the pin string. |
| 5 | `revolver/proposal.py` | NEW-file-only repair-path core: `NewFile` + `RepairProposal` containers and `propose()`; `validate()` enforces hard rule 7. |
| 6 | `revolver/fixes.py` | Concrete per-failure-mode fix builders (`build_driver_death_fix`, `build_wall_kill_fix`, `build_stall_kill_fix`, `build_client_timeout_fix`, `build_inner_wall_fix`, `build_outer_freshness_fix`, `build_none_fix`) + the `FIX_BUILDERS` registry. |
| 7 | `revolver/launch_plan.py` | Deterministic dry-run launch-plan derivation (command, marker, endpoint pin, two wall-clock budgets); enforces `request_timeout >= outer_wall` and one pipeline per endpoint. |
| 8 | `revolver/manifest.py` | The unified, versioned, serializable `ProposalManifest` (diagnosis + repair path + launch plan); composes `propose()` + `build_launch_plan()` and exposes a whole-manifest `validate()`. |
| 9 | `revolver/validation.py` | Pure, dry-run content validation: static Python-syntax + import checks on each NEW file, and command-shape checks on the launch plan. |
| 10 | `revolver/deploy.py` | Deployment + relaunch execution for a validated `ProposalManifest`; `deploy_manifest` (additions-only, approval-gated) and `relaunch` (no process kill). |
| 11 | `revolver/relaunch.py` | Deterministic relaunch planning + verification: `first_not_done_cycle`, `plan_relaunch`, and `verify_relaunch` (marker + driver alive). |
| 12 | `revolver/observe.py` | The read-only observer half: parses `cycles.out` markers, trajectory outcomes, and git merge commits; reports done/in-flight/gaps and composes the recurrence verdict and final report. |
| 13 | `revolver/derive.py` | Derive-by-reference: read a predecessor read-only, apply exactly one stated edit, emit a NEW versioned file; verification by construction (compile + diff == stated lines). |
| 14 | `revolver/triple.py` | The pinned derivation baseline carried by REFERENCE only: meta-dir path, pinned sha256 checksums, and `verify_triple`/`resolve` that fail loud on any mismatch. |

## Dependency edges

Edges are `A -> B` meaning "module A imports module B" (runtime or `TYPE_CHECKING`).
`__init__.py` is the package root and is imported by no other module.

| Importer | Imports |
|----------|---------|
| `diagnosis` | `sentry_client` (TYPE_CHECKING + lazy) |
| `sentry_client` | `diagnosis` |
| `proposal` | `diagnosis`, `fixes` (lazy) |
| `fixes` | `diagnosis`, `proposal`, `derive` (lazy) |
| `launch_plan` | `diagnosis`, `proposal` (TYPE_CHECKING) |
| `manifest` | `diagnosis`, `launch_plan`, `proposal` |
| `validation` | `launch_plan`, `manifest` (TYPE_CHECKING) |
| `deploy` | `manifest` (TYPE_CHECKING) |
| `relaunch` | `manifest` (TYPE_CHECKING) |
| `observe` | `diagnosis` (TYPE_CHECKING) |
| `derive` | — (leaf; no intra-package imports) |
| `triple` | — (leaf; no intra-package imports) |
| `sentry_pin` | — (leaf; no intra-package imports) |
| `__init__` | — (package root; imported by no other module) |

The dependency graph is a DAG rooted at the leaves (`derive`, `triple`,
`sentry_pin`) and flowing up through `diagnosis` → `proposal`/`fixes` →
`manifest` → `deploy`/`relaunch`/`validation`/`observe`. `diagnosis` and
`sentry_client` form a deliberate cycle broken by `TYPE_CHECKING` + lazy
import so the runtime import order stays acyclic.
