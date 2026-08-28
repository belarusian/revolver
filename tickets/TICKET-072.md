# TICKET-072 — driver-variant template for the outer-freshness fix

**Status:** Open
**Cycle:** 16
**Build Order row:** Outer-freshness guard — run-v4 meta-derivation (16)

## Capability
`build_outer_freshness_fix` also emits a driver-variant template that reuses the
existing launch-plan machinery: `RUN=.../run-v4.py` (repointed at the generated runner),
endpoints verbatim (FIVE_BASE_URL / FIVE_MODEL / FIVE_LARGE_URL / FIVE_LARGE_MODEL /
FIVE_MAX_TOKENS), and `FIVE_REQUEST_TIMEOUT >= outer wall`.

## Acceptance
- Driver content contains `RUN=` pointing at the run-v4 runner path.
- Driver content exports `FIVE_REQUEST_TIMEOUT` with a value >= the diagnosis outer wall.
- Endpoint pins are present verbatim.
- Docstring carries diff-from-predecessor + evidence.
