# TICKET-008: pyproject.toml — declare sentry as a pinned git dependency

Status: DONE
**Title:** Declare sentry as a pinned git dependency in `[project.optional-dependencies]`
using the loop-doctor pattern (`name @ git+<url>@<full-sha>`), never a live tree.

**Evidence:**
- `pyproject.toml` currently has `dependencies = []` and no `[project.optional-dependencies]`.
- `revolver/sentry_pin.py::DEFAULT_SENTRY_PIN` = `sentry @ git+https://github.com/belarusian/sentry.git@9713735c0b588e271f277a4b2b9f377ffbe2681c`.
- The loop-doctor pattern (see `sentry_pin.py` docstring) pins optional deps as
  `name @ git+https://github.com/<org>/<repo>.git@<full-sha>`.

**Impact:** sentry is not declared as a dependency at all, so the "pinned git dependency"
mission is unmet and `pip install revolver[sentry]` would do nothing.

**Suggestion:**
- Add `[project.optional-dependencies]` with
  `sentry = ["sentry @ git+https://github.com/belarusian/sentry.git@9713735c0b588e271f277a4b2b9f377ffbe2681c"]`.
- Keep the base `dependencies = []` (stdlib-only core).

DONE — verified implemented in sentry_pin.py (tests in test_sentry_pin.py); closed out in Cycle 36.
