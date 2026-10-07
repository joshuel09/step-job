"""Quickstart Scenarios 3 and 7 — nothing is invented to fill a blank.

FR-013: a section the user has not filled in is empty. Not a placeholder, not
"N/A", not a sample row, not a plausible guess. The labels stay, so the user
can see what is blank before printing (FR-022c), but nothing follows them.

This is the rule most easily broken by a later change that tries to be helpful,
so the strongest test here is exact: a profile holding only a name produces a
document whose every line is a label or that name. Anything a future change
invents to fill a gap appears as a line this list does not expect.

FR-022: there is no 性別 field. Not an empty box inviting completion; nothing.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/rirekisho"

# The whole document for a profile holding only a name, line by line. Changing
# a label means changing this list — deliberately, in review.
NAME_ONLY = [
    "履歴書",
    "ふりがな",
    "氏名 鈴木花子",
    "生年月日",
    "現住所",
    "電話",
    "メール",
    "写真貼付欄",
    "学歴・職歴",
    "以上",
    "免許・資格",
    "本人希望記入欄",
    "志望の動機",
]

IDENTITY_LABELS = ("ふりがな", "生年月日", "現住所", "電話", "メール")


def _lines(content: bytes) -> list[str]:
    """Each line of the document, with the layout's spacing collapsed."""
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
    lines = (re.sub(r"[\s　]+", " ", line).strip() for line in text.splitlines())
    return [line for line in lines if line]


def _generate(client, auth_headers) -> list[str]:
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return _lines(response.content)


def _between(lines: list[str], start: str, end: str) -> list[str]:
    return lines[lines.index(start) + 1 : lines.index(end)]


@pytest.fixture
def profile(session, user_id):
    from app.career import service

    return service.get_or_create_profile(session, user_id)


@pytest.fixture
def name_only(session, profile):
    """The least a 履歴書 can be produced from."""
    from app.career import models

    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Hanako Suzuki",
            full_name_japanese="鈴木花子",
        )
    )
    session.flush()
    return profile


class TestNothingIsInvented:
    def test_a_name_only_profile_produces_only_labels_and_the_name(
        self, client, auth_headers, name_only
    ):
        assert _generate(client, auth_headers) == NAME_ONLY

    @pytest.mark.parametrize("label", IDENTITY_LABELS)
    def test_a_blank_identity_field_is_its_label_alone(
        self, client, auth_headers, name_only, label
    ):
        assert label in _generate(client, auth_headers)

    def test_an_empty_history_is_only_ijou(self, client, auth_headers, name_only):
        """Scenario 3: the heading exists and no row follows but the closing one."""
        lines = _generate(client, auth_headers)
        assert _between(lines, "学歴・職歴", "免許・資格") == ["以上"]

    def test_no_certifications_means_nothing_under_the_heading(
        self, client, auth_headers, name_only
    ):
        lines = _generate(client, auth_headers)
        assert _between(lines, "免許・資格", "本人希望記入欄") == []


class TestOneEmptySectionBesideAFullOne:
    """An empty section stays empty even when its neighbour has rows to borrow."""

    def test_roles_without_education_add_no_education_rows(
        self, client, auth_headers, session, name_only
    ):
        from app.career import models

        session.add(
            models.WorkExperience(
                profile_id=name_only.id,
                employer_name="株式会社サンプル",
                employer_name_normalised="サンプル",
                job_title="エンジニア",
                started_on=date(2013, 4, 1),
                source_language=models.Locale.ja,
            )
        )
        session.flush()

        history = " ".join(_between(_generate(client, auth_headers), "学歴・職歴", "免許・資格"))
        assert "入学" not in history
        assert "卒業" not in history
        assert "株式会社サンプル" in history

    def test_education_without_roles_adds_no_employment_rows(
        self, client, auth_headers, session, name_only
    ):
        from app.career import models

        session.add(
            models.Education(
                profile_id=name_only.id,
                institution="サンプル大学",
                started_on=date(2009, 4, 1),
                ended_on=date(2013, 3, 31),
            )
        )
        session.flush()

        history = " ".join(_between(_generate(client, auth_headers), "学歴・職歴", "免許・資格"))
        for event in ("入社", "退社", "現在に至る"):
            assert event not in history
        assert "サンプル大学" in history


class TestNoGenderField:
    """FR-022: omitted, at every setting and whatever the profile holds."""

    MARKERS = ("性別", "男・女", "男 ・ 女")

    def test_absent_from_a_name_only_document(self, client, auth_headers, name_only):
        text = " ".join(_generate(client, auth_headers))
        assert [m for m in self.MARKERS if m in text] == []

    @pytest.mark.parametrize(
        "body",
        [{"date_convention": "wareki"}, {"paper_size": "b5"}],
        ids=["wareki", "b5"],
    )
    def test_absent_at_every_setting(self, client, auth_headers, rirekisho_profile, body):
        response = client.post(PATH, headers=auth_headers, json=body)
        assert response.status_code == 200, response.text
        text = " ".join(_lines(response.content))
        assert [m for m in self.MARKERS if m in text] == []


class TestNoNameIsRefused:
    """FR-015: a document with a blank where a name belongs is not a 履歴書."""

    def test_no_identity_is_refused_naming_the_identity(self, client, auth_headers, profile):
        response = client.post(PATH, headers=auth_headers, json={})

        assert response.status_code == 422
        failures = response.json()["failures"]
        assert [f["field"] for f in failures] == ["identity"]
        assert "name" in failures[0]["reason"]

    def test_a_blank_name_is_refused_naming_the_field(self, client, auth_headers, session, profile):
        """An identity record exists, but the name in it is empty."""
        from app.career import models

        session.add(models.Identity(profile_id=profile.id, full_name_latin=""))
        session.flush()

        response = client.post(PATH, headers=auth_headers, json={})

        assert response.status_code == 422
        assert [f["field"] for f in response.json()["failures"]] == ["identity.full_name_latin"]

    def test_a_refusal_produces_no_document(self, client, auth_headers, profile):
        response = client.post(PATH, headers=auth_headers, json={})
        assert response.headers["content-type"].startswith("application/json")
        assert not response.content.startswith(b"%PDF")
