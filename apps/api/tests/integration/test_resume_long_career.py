"""A career too long for one page (FR-007).

The document runs on. It does not drop the oldest role, truncate a
description, or shrink the type to fit — shortening a resume is the user
choosing what to leave out, which is what `include_skills` is for, and
never the renderer deciding on their behalf.

The continuation marker is here rather than in a renderer unit test for a
reason worth recording: a document that fits on one page never reaches the
code that draws it, so the only test that can catch an English page
carrying 自己PR（続き） is one that forces a second page.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/resume"
ROLES = 24


@pytest.fixture
def long_career(session, user_id):
    """Two dozen roles with descriptions, so the document must run on.

    Every employer is numbered, so a dropped one is identifiable rather
    than merely a shorter document that still looks plausible.
    """
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id, full_name_latin="Taro Yamada", email="taro@example.com"
        )
    )

    for number in range(ROLES):
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name=f"Employer {number:02d} Limited",
                employer_name_normalised=f"employer{number:02d}",
                job_title=f"Engineer Grade {number:02d}",
                started_on=date(1990 + number, 4, 1),
                ended_on=date(1991 + number, 3, 31),
                description=(
                    "Built and maintained the billing service, and the "
                    "reporting that sat on top of it, for a team that grew "
                    "over the period."
                ),
                source_language=models.Locale.en,
            )
        )
    session.flush()
    return profile


@pytest.fixture
def document(client, auth_headers, long_career):
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response


def _pages(pdf: bytes) -> list[str]:
    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages]


def _text(pdf: bytes) -> str:
    return re.sub(r"\s+", " ", "\n".join(_pages(pdf)))


class TestNothingIsLost:
    def test_the_document_runs_to_more_than_one_page(self, document):
        assert len(_pages(document.content)) > 1

    def test_every_role_is_in_it(self, document):
        text = _text(document.content)
        missing = [n for n in range(ROLES) if f"Employer {n:02d} Limited" not in text]

        assert not missing, f"roles dropped: {missing}"

    def test_the_oldest_role_is_the_one_that_would_have_been_dropped(self, document):
        """Named separately because it is the one a renderer that gave up
        would lose, and a test asserting "most of them" would pass."""
        assert f"Employer {ROLES - 1:02d} Limited" in _text(document.content)

    def test_the_page_count_matches_the_file(self, document):
        """The interface tells the user their resume runs long using this
        header, so a count that drifts from the file misleads them about
        the document they are holding."""
        assert int(document.headers["X-Document-Pages"]) == len(_pages(document.content))


class TestThePageItRunsOnto:
    def test_a_carried_section_says_so_in_english(self, document):
        """`Page` defaults its continuation marker to （続き）, which is
        right for a 履歴書 and would be a Japanese convention appearing in a
        document that has none."""
        assert "Experience (continued)" in _text(document.content)

    def test_and_not_in_japanese(self, document):
        assert "（続き）" not in _text(document.content)
        assert "続き" not in _text(document.content)
