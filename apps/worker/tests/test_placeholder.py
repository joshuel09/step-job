def test_worker_package_imports():
    """The purge actor arrives with Phase 6; this keeps the suite collectable."""
    import app

    assert app is not None
