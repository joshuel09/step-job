"""Shared fixtures: a clean database and an authenticated caller."""

import os
import uuid
from collections.abc import Iterator

import pytest
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://stepjob:stepjob@localhost:5432/stepjob_test",
)


def _ensure_database_exists(url: str) -> None:
    """Create the test database if it is not there yet.

    Keeps a fresh checkout and continuous integration on the same path: bring up
    Postgres and run the suite, with no manual createdb step in between.
    """
    target = make_url(url)
    admin = target.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT", future=True)
    try:
        with engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_database_exists(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine) -> Iterator[Session]:
    """A session rolled back after each test, so cases cannot leak into each other."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    """A verified caller. The API derives the owner from this and never from a path."""
    return {"Authorization": f"Bearer {user_id}"}


@pytest.fixture
def client(session) -> Iterator[TestClient]:
    """A client whose requests run inside the test's rolled-back session."""
    from app.db.session import get_session

    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
