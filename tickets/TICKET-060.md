# TICKET-060 — README: what revolver is (the closed loop)

Status: DONE
**Cycle:** 13 (Docs + release)
**Target:** `README.md` (new file)
**Capability:** A top-level README that states what revolver is — the hands of the
closed loop: sentry (eyes) diagnoses, revolver proposes a minimal NEW-file-only
versioned repair path, a human approves (plan/apply split), the pipeline relaunches
on the new path, and the observer reports whether the diagnosed failure mode recurred.

**Acceptance:**
- Every claim is true of the code on main (written FROM the gate log, not ambition).
- Names the closed-loop role and the two founding fix classes as the acceptance
  criteria the build was tested against.
- No invented command lines: the quickstart uses the real library entry points
  (diagnose / build_manifest / deploy_manifest / relaunch / render_final_report).

DONE — verified in README.md (The closed loop section); closed out in Cycle 36.
