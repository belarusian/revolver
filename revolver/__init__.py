"""revolver — deterministic, stdlib-only repair-path generator.

Consumes sentry check/rescue diagnoses and produces versioned, additive-only
repair paths for four pipelines. Every generated file is NEW (never mutates an
existing one) and carries a docstring stating its diff from the predecessor and
the evidence motivating it.
"""

__version__ = "0.0.1"
