"""Worker tests reuse the API's models against a real database."""

import os
import uuid
from collections.abc import Iterator

import pytest
from app.db.base import Base
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://stepjob:stepjob@localhost:5432/stepjob_test",
)


def _ensure_database_exists(url: str) -> None:
    target = make_url(url)
    engine = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
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
    engine.dispose()


@pytest.fixture
def session(engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    db = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()
