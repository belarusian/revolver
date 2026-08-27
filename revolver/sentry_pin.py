"""revolver.sentry_pin — resolve sentry as a pinned git dependency.

Diff from predecessor: NEW module (no predecessor in this repo).
Evidence: the loop-doctor pattern pins optional dependencies as
``name @ git+https://github.com/<org>/<repo>.git@<full-sha>`` in
``[project.optional-dependencies]`` (loop-doctor/proj/pyproject.toml). The mission
requires sentry to be consumed as a pinned git dependency — "the loop-doctor
pattern - never a live tree." A full-sha pin makes the consumed revision
reproducible; a branch/tag/live tree would not.

This module is pure and stdlib-only: it parses, renders, and validates the pin
requirement string. It does not perform any git I/O (that is the installer's job).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Defaults (the pinned sentry revision)
# ---------------------------------------------------------------------------

DEFAULT_SENTRY_NAME = "sentry"
DEFAULT_SENTRY_URL = "https://github.com/belarusian/sentry.git"
DEFAULT_SENTRY_SHA = "9713735c0b588e271f277a4b2b9f377ffbe2681c"


@dataclass(frozen=True)
class SentryPin:
    """A pinned git dependency for sentry (loop-doctor pattern).

    Attributes:
        name: The package name (e.g. "sentry").
        url: The git URL without the ``git+`` prefix and without the ``@<sha>``
            suffix (e.g. "https://github.com/belarusian/sentry.git").
        sha: The full 40-hex commit sha to pin to.
    """

    name: str
    url: str
    sha: str


DEFAULT_SENTRY_PIN = SentryPin(
    name=DEFAULT_SENTRY_NAME,
    url=DEFAULT_SENTRY_URL,
    sha=DEFAULT_SENTRY_SHA,
)


# ---------------------------------------------------------------------------
# Parsing / rendering
# ---------------------------------------------------------------------------

# name @ git+<url>@<sha>
#   - name: non-space, non-@ tokens
#   - url:  https://... ending in .git (no @ inside)
#   - sha:  40 hex chars
_REQ_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*@\s*"
    r"git\+(?P<url>https://[^\s@]+\.git)@(?P<sha>[0-9a-f]{40})$"
)


def parse_requirement(req: str) -> SentryPin:
    """Parse a ``name @ git+<url>@<sha>`` requirement into a :class:`SentryPin`.

    Raises:
        ValueError: if the requirement is malformed (wrong scheme, missing .git,
            short/branch sha, etc.).
    """
    m = _REQ_RE.match(req.strip())
    if not m:
        raise ValueError(f"malformed sentry pin requirement: {req!r}")
    return SentryPin(name=m.group("name"), url=m.group("url"), sha=m.group("sha"))


def render_requirement(pin: SentryPin) -> str:
    """Render a :class:`SentryPin` back to ``name @ git+<url>@<sha>``."""
    return f"{pin.name} @ git+{pin.url}@{pin.sha}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_pin(pin: SentryPin) -> bool:
    """Return True only if the pin is a valid full-sha git dependency.

    Rules (loop-doctor pattern, never a live tree):
      * ``sha`` is exactly 40 lowercase hex chars (a full commit sha — not a
        branch, tag, or short sha).
      * ``url`` starts with ``https://`` and ends with ``.git``.
      * ``name`` is non-empty.
    """
    if not pin.name or not pin.name.strip():
        return False
    if not _SHA_RE.match(pin.sha):
        return False
    if not pin.url.startswith("https://"):
        return False
    return pin.url.endswith(".git")
