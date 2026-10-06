from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def engine():
    """Тестовый engine. Схема создаётся настоящими миграциями Alembic,
    поэтому заодно проверяется, что миграции работают."""
    test_url = settings.test_database_url
    # Защита от случайного запуска тестов на рабочей БД
    if not (make_url(test_url).database or "").endswith("_test") or test_url == settings.database_url:
        pytest.exit("TEST_DATABASE_URL должен указывать на отдельную БД с суффиксом _test", returncode=2)

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    eng = create_engine(test_url)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def clean_db(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, projects, tasks RESTART IDENTITY CASCADE"))

@pytest.fixture
def client(engine):
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    def _make(name="Ivan", email="ivan@example.com"):
        r = client.post("/users", json={"name": name, "email": email})
        assert r.status_code == 201, r.text
        return r.json()
    return _make


@pytest.fixture
def make_project(client):
    def _make(name="Project", description=None):
        r = client.post("/projects", json={"name": name, "description": description})
        assert r.status_code == 201, r.text
        return r.json()
    return _make


@pytest.fixture
def make_task(client):
    def _make(project_id, title="Task", **extra):
        r = client.post("/tasks", json={"title": title, "project_id": project_id, **extra})
        assert r.status_code == 201, r.text
        return r.json()
    return _make
