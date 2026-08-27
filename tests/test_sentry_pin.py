"""Tests for revolver.sentry_pin — parse/render round-trip and validation."""

from __future__ import annotations

import pytest

from revolver.sentry_pin import (
    DEFAULT_SENTRY_PIN,
    SentryPin,
    parse_requirement,
    render_requirement,
    validate_pin,
)


class TestParseRender:
    def test_parse_default(self):
        req = "sentry @ git+https://github.com/belarusian/sentry.git@9713735c0b588e271f277a4b2b9f377ffbe2681c"
        pin = parse_requirement(req)
        assert pin == DEFAULT_SENTRY_PIN
        assert pin.name == "sentry"
        assert pin.url == "https://github.com/belarusian/sentry.git"
        assert pin.sha == "9713735c0b588e271f277a4b2b9f377ffbe2681c"

    def test_round_trip(self):
        pin = SentryPin(
            name="sentry",
            url="https://github.com/belarusian/sentry.git",
            sha="a" * 40,
        )
        assert parse_requirement(render_requirement(pin)) == pin

    def test_render_format(self):
        assert (
            render_requirement(DEFAULT_SENTRY_PIN)
            == "sentry @ git+https://github.com/belarusian/sentry.git@9713735c0b588e271f277a4b2b9f377ffbe2681c"
        )

    def test_parse_rejects_short_sha(self):
        with pytest.raises(ValueError, match="malformed"):
            parse_requirement("sentry @ git+https://github.com/belarusian/sentry.git@abc123")

    def test_parse_rejects_branch(self):
        with pytest.raises(ValueError, match="malformed"):
            parse_requirement("sentry @ git+https://github.com/belarusian/sentry.git@main")

    def test_parse_rejects_non_https(self):
        with pytest.raises(ValueError, match="malformed"):
            parse_requirement(
                "sentry @ git+http://github.com/belarusian/sentry.git@" + "a" * 40
            )

    def test_parse_rejects_missing_git_suffix(self):
        with pytest.raises(ValueError, match="malformed"):
            parse_requirement(
                "sentry @ git+https://github.com/belarusian/sentry@" + "a" * 40
            )

    def test_parse_rejects_no_git_prefix(self):
        with pytest.raises(ValueError, match="malformed"):
            parse_requirement(
                "sentry @ https://github.com/belarusian/sentry.git@" + "a" * 40
            )


class TestValidatePin:
    def test_accepts_default(self):
        assert validate_pin(DEFAULT_SENTRY_PIN) is True

    def test_rejects_short_sha(self):
        assert validate_pin(SentryPin("sentry", "https://x/y.git", "abc123")) is False

    def test_rejects_uppercase_sha(self):
        assert validate_pin(SentryPin("sentry", "https://x/y.git", "A" * 40)) is False

    def test_rejects_branch_sha(self):
        assert validate_pin(SentryPin("sentry", "https://x/y.git", "main")) is False

    def test_rejects_non_https(self):
        assert validate_pin(SentryPin("sentry", "http://x/y.git", "a" * 40)) is False

    def test_rejects_missing_git_suffix(self):
        assert validate_pin(SentryPin("sentry", "https://x/y", "a" * 40)) is False

    def test_rejects_empty_name(self):
        assert validate_pin(SentryPin("", "https://x/y.git", "a" * 40)) is False
