# TICKET-061 — README: quickstart (library-based, verified against modules)

**Cycle:** 13 (Docs + release)
**Target:** `README.md` (quickstart section)
**Capability:** A quickstart showing the diagnose -> propose -> approve -> deploy ->
relaunch -> observe flow as it actually exists in the code. There is NO CLI entry
point (no console_scripts, no `def main`, no argparse) — the `revolver plan` /
`revolver apply` / `revolver launch` strings in the launch-plan command are *generated
text*, not real commands. The quickstart must be library-based.

**Acceptance:**
- Each shown call matches a real public signature:
  `diagnose(project_dir)`, `build_manifest(diagnosis)`, `deploy_manifest(manifest,
  base_dir=..., approved=...)`, `relaunch(manifest)`, `render_final_report(diagnosis)`.
- No invented flags or subcommands.
