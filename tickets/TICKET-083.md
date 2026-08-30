# TICKET-083 — README module table missing derive.py and triple.py

**Status: DONE**

> Cycle 29: added derive.py + triple.py rows; module table now 13 rows (matches 13 modules).
**Source: Cycle 28 synthesis audit — toolchain-pin verification**

## Evidence
- `revolver/` contains 14 `.py` files: `__init__.py`, `deploy.py`, `derive.py`,
  `diagnosis.py`, `fixes.py`, `launch_plan.py`, `manifest.py`, `observe.py`,
  `proposal.py`, `relaunch.py`, `sentry_client.py`, `sentry_pin.py`,
  `triple.py`, `validation.py` (13 modules + `__init__.py`)
- README.md "Modules" table has 11 rows (verified: `grep -c '^| `' README.md`
  → 11). Listed: diagnosis, sentry_client, sentry_pin, proposal, fixes,
  manifest, launch_plan, validation, deploy, relaunch, observe.
- Missing from table: `derive.py`, `triple.py`.
- `revolver/derive.py` docstring: "derive-by-reference: predecessor-in,
  versioned-variant-out. Evidence: Build Order row 'Derive-by-reference | 17-19'
  + TICKET-076."
- `revolver/triple.py` docstring: "the pinned derivation baseline, carried by
  REFERENCE only. Evidence: Build Order row 'Derive-by-reference | 17-19' +
  TICKET-075."
- Both modules have tests: `tests/test_derive.py`, `tests/test_triple.py`

## Impact
A newcomer reading the README sees 11 modules but the package has 13 (excluding
`__init__.py`). The derive-by-reference architecture (cycles 17-19) is invisible
in the primary documentation. The README's claim "One row per module in
`revolver/`" is false.

## Suggestion
Add two rows to the README module table:
- `derive.py` — derive-by-reference: predecessor-in, versioned-variant-out.
  Core of the derive-by-reference procedure replacing value-embedding generators.
- `triple.py` — the pinned derivation baseline, carried by REFERENCE only.
  Artifacts carry REFERENCES (paths + checksums), never VALUES.
