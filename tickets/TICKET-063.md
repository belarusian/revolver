# TICKET-063 — GitHub repo About (description + topics) via gh

**Cycle:** 13 (Docs + release)
**Target:** GitHub repo metadata (belarusian/revolver)
**Capability:** Set the repo About: a one-line description (the closed-loop role) +
topics (pipeline, rescue, four, sentry) via `gh repo edit`.

**Acceptance:**
- `gh repo edit belarusian/revolver --description "..." --add-topic pipeline
  --add-topic rescue --add-topic four --add-topic sentry`.
- Verified with `gh repo view`.
