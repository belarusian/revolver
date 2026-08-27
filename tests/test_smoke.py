"""Smoke test: revolver imports cleanly."""


def test_import_revolver():
    import revolver

    assert revolver.__version__
