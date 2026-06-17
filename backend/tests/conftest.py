from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _skip_lifespan_db_check(monkeypatch):
    """app.main's lifespan calls init_db() on startup, which hits real Supabase.
    Tests never need that side effect, so it's stubbed out for every test.
    """
    monkeypatch.setattr("app.main.init_db", AsyncMock())


@pytest.fixture(autouse=True)
def _default_db_override():
    """Default every test's get_db dependency to a MagicMock so the route layer
    never constructs a real Supabase client (which requires real SUPABASE_URL/
    SUPABASE_SERVICE_ROLE_KEY env vars — not available in CI). Tests that need
    specific data set app.dependency_overrides[get_db] themselves; that runs
    after this fixture and simply replaces the mapping for that test.
    """
    from app.api.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """check_rate_limit's store is module-level global state shared across tests."""
    from app.utils.security import _rate_limit_store

    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()
