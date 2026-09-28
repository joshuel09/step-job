"""Quickstart Scenario 8 — import a 職務経歴書 as it is written.

Two things have to hold at once. The era date must convert, because a profile
stores calendar dates. And nothing may be translated, because the entry belongs
to the language its author wrote it in (FR-010, and FR-009 of feature 001).

The evidence carries the document's own words, so a user confirms the conversion
rather than trusting it.
"""

from pathlib import Path

import pytest
from app.ai.fake import FakeAIProvider, FakeBehaviour
from app.career import proposals
from app.career import service as career_service
from app.imports import service
from app.imports.models import ImportStatus, SourceKind

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

JAPANESE_SOURCE = (
    "職務経歴書\n"
    "\n"
    "職務要約\n"
    "サンプル株式会社にて社内システムの開発を担当しました。\n"
    "\n"
    "職務経歴\n"
    "エンジニア、サンプル株式会社\n"
    "令和3年4月から令和6年3月まで\n"
    "社内向けサービスの開発および保守を担当。\n"
)


@pytest.fixture
def profile(session, user_id):
    return career_service.get_or_create_profile(session, user_id)


def _run(session, profile, source: str):
    record = service.create(session, profile, SourceKind.pasted_text)
    return service.run(session, profile, record, source, FakeAIProvider(FakeBehaviour.extract))


def test_a_japanese_resume_produces_proposals(session, profile):
    record = _run(session, profile, JAPANESE_SOURCE)

    assert record.status is ImportStatus.completed
    assert record.entry_count >= 1


def test_the_entry_records_japanese_as_its_language(session, profile):
    _run(session, profile, JAPANESE_SOURCE)

    queued = proposals.list_for(session, profile)
    assert queued[0].payload["source_language"] == "ja"


def test_nothing_is_translated(session, profile):
    """The entry belongs to the language its author wrote it in."""
    _run(session, profile, JAPANESE_SOURCE)

    payload = proposals.list_for(session, profile)[0].payload
    assert payload["employer_name"] == "サンプル株式会社"
    assert payload["job_title"] == "エンジニア"


def test_an_era_date_becomes_a_calendar_date(session, profile):
    _run(session, profile, JAPANESE_SOURCE)

    payload = proposals.list_for(session, profile)[0].payload
    assert payload["started_on"] == "2021-04-01"


def test_the_evidence_keeps_the_documents_own_words(session, profile):
    """So the user confirms the conversion rather than trusting it (FR-011)."""
    _run(session, profile, JAPANESE_SOURCE)

    evidence = proposals.list_for(session, profile)[0].evidence
    assert "令和3年4月" in evidence["started_on"]["quote"]


def test_an_english_document_still_records_english(session, profile):
    english = "Software Engineer, Example Corp\nApril 2021 to March 2024\nBuilt services."
    _run(session, profile, english)

    assert proposals.list_for(session, profile)[0].payload["source_language"] == "en"


def test_a_japanese_word_document_is_read_including_its_tables(session, profile):
    """A 職務経歴書 routinely puts its substance in tables, not paragraphs."""
    from app.imports.documents import extract_text

    text = extract_text((FIXTURES / "example-resume-ja.docx").read_bytes())

    assert "職務経歴書" in text
    assert "令和3年4月" in text

    record = _run(session, profile, text)
    assert record.status is ImportStatus.completed
