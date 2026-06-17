from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _skip_lifespan_db_check(monkeypatch):
    """app.main's lifespan calls init_db() on startup, which hits real Supabase.
    Tests never need that side effect, so it's stubbed out for every test.
    """
    monkeypatch.setattr("app.main.init_db", AsyncMock())


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """check_rate_limit's store is module-level global state shared across tests."""
    from app.utils.security import _rate_limit_store

    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()
