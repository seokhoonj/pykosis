"""Shared test fixtures for pykosis."""

from __future__ import annotations

import pytest

from pykosis import _config


@pytest.fixture(autouse=True)
def _reset_credbox_binding(monkeypatch):
    """Reset the cached credbox facade and the store-binding env vars around every test,
    so a binding one test sets (or a dev's shell) cannot leak into another."""
    monkeypatch.delenv("PYKOSIS_STORE_APP", raising=False)
    monkeypatch.delenv("PYKOSIS_NAMESPACE", raising=False)
    _config._get_credentials.cache_clear()
    yield
    _config._get_credentials.cache_clear()
