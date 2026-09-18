import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.core.database import get_engine, get_session_factory


@pytest.fixture
def seeded_database(tmp_path, monkeypatch):
    database_file = tmp_path / "eventease-test.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "local-test-secret-with-at-least-32-characters")
    monkeypatch.setenv("ENABLE_DEMO_LOGIN", "true")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.upgrade(config, "head")

    from app.seed import seed_demo_data

    with get_session_factory()() as session:
        seed_demo_data(session)
        seed_demo_data(session)

    yield

    get_session_factory.cache_clear()
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()
