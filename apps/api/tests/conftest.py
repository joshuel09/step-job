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


# --- feature 002: the model boundary ----------------------------------------

SAMPLE_RESUME = """\
Software Engineer, Example Corp
April 2021 to March 2024
Built and maintained internal services.

Skills: Ruby, PostgreSQL, TypeScript
"""


@pytest.fixture
def source_text() -> str:
    """Invented career text. No real person's details belong in a fixture."""
    return SAMPLE_RESUME


@pytest.fixture
def fake_provider():
    """A provider that never reaches the network.

    Returns a factory so a test can pick the behaviour it needs — honest
    extraction, a fabricated quote, a transient outage — without patching.
    """
    from app.ai.fake import FakeAIProvider

    def make(behaviour: str = "extract", **kwargs):
        return FakeAIProvider(behaviour, **kwargs)

    return make


# --- feature 003: a profile complete enough to produce a 履歴書 ---------------


@pytest.fixture
def rirekisho_profile(session, user_id):
    """A profile with everything a 履歴書 needs, in invented content.

    One ongoing role and one finished one, so the table exercises both 退社 and
    現在に至る without a test having to build them.
    """
    from datetime import date

    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)

    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Taro Yamada",
            full_name_japanese="山田太郎",
            furigana="ヤマダタロウ",
            date_of_birth=date(1990, 5, 15),
            address="東京都新宿区サンプル1-2-3",
        )
    )
    session.add(
        models.Education(
            profile_id=profile.id,
            institution="サンプル大学",
            qualification="学士",
            started_on=date(2009, 4, 1),
            ended_on=date(2013, 3, 31),
        )
    )
    session.add(
        models.WorkExperience(
            profile_id=profile.id,
            employer_name="株式会社サンプル",
            employer_name_normalised="サンプル",
            job_title="エンジニア",
            started_on=date(2013, 4, 1),
            ended_on=date(2021, 3, 31),
            source_language=models.Locale.ja,
        )
    )
    session.add(
        models.WorkExperience(
            profile_id=profile.id,
            employer_name="Example Corp",
            employer_name_normalised="example",
            job_title="Software Engineer",
            started_on=date(2021, 4, 1),
            ended_on=None,
            source_language=models.Locale.en,
        )
    )
    session.flush()
    return profile
