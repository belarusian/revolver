# TICKET-062 — README: module table mirroring each module's docstring

Status: DONE
**Cycle:** 13 (Docs + release)
**Target:** `README.md` (module table)
**Capability:** One row per module in revolver/ (diagnosis, sentry_client, sentry_pin,
proposal, fixes, manifest, launch_plan, validation, deploy, relaunch, observe)
mirroring each module's docstring (its diff-from-predecessor + evidence).

**Acceptance:**
- 11 rows, one per module, each summarizing the module's stated role.
- The design invariants are stated: additive files only (hard rule 7 — never mutate an
  existing file), human approval gate between proposal and launch, never kills
  processes (that stays sentry's), never touches other projects' proj/ repos, never
  changes endpoint allocation, deterministic + stdlib-only with overridable I/O seams.

DONE — verified in README.md (Modules table); closed out in Cycle 36.
