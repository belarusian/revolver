# TICKET-004: revolver.sentry_pin — resolve sentry as a pinned git dependency

**Title:** Resolve sentry as a pinned git dependency (loop-doctor pattern: full-sha pin, never a live tree).

**Evidence:** loop-doctor pins optional deps as
`name @ git+https://github.com/belarusian/<repo>.git@<full-sha>` in
`[project.optional-dependencies]` (loop-doctor/proj/pyproject.toml lines 25-26).
Sentry's remote is `https://github.com/belarusian/sentry.git`; current full sha
`9713735c0b588e271f277a4b2b9f377ffbe2681c`. The mission: "Sentry is consumed as a
pinned git dependency ... the loop-doctor pattern - never a live tree."

**Impact:** Without a pin resolver, revolver cannot declare/verify the exact sentry
revision it consumes; a live tree would make diagnoses non-reproducible.

**Suggestion:** Add `revolver/sentry_pin.py` with a `SentryPin` dataclass (name, url,
sha), `parse_requirement(req) -> SentryPin`, `render_requirement(pin) -> str`,
`validate_pin(pin)` (full 40-hex sha, https git+ url, no branch/tag), and a
`DEFAULT_SENTRY_PIN` constant. Pure, stdlib-only.
