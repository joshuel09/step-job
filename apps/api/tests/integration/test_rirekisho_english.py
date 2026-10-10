"""Quickstart Scenario 5 — English is reported, never translated.

An entry the user wrote in English appears in English. Translating a job title
or an employer's name into Japanese would be a claim the user never made, which
Principle IV forbids however helpful it looks (research.md R-001).

"Nothing in the document is Japanese the user did not write" is tested by
subtraction: remove every value the user entered and every fixed part of the
form, and no Japanese may remain. The form's labels (履歴書, 学歴・職歴, 以上 and
so on) are the product's, not a claim about the user. Listing them here means a
new piece of Japanese in the document has to be added to this list on purpose,
in review, rather than appearing unremarked.
"""

import io
import re
from datetime import date

import pytest
from app.imports.dates import ERA_STARTS
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/rirekisho"

# The form's own words: labels, headings and the table's fixed events.
FORM = (
    "履歴書",
    "ふりがな",
    "氏名",
    "生年月日",
    "現住所",
    "電話",
    "メール",
    "写真貼付欄",
    "学歴・職歴",
    "免許・資格",
    "本人希望記入欄",
    "志望の動機",
    "入学",
    "卒業",
    "入社",
    "退社",
    "現在に至る",
    "以上",
)

# A date in either convention: 2013年4月, 平成25年4月, 令和元年5月1日.
_ERAS = "|".join(name for name, _ in ERA_STARTS)
DATE = re.compile(rf"(?:{_ERAS})?(?:\d+|元)年\d+月(?:\d+日)?")

# Hiragana, katakana, CJK ideographs and full-width forms. The ideographic space
# is layout, not content, and is collapsed before this runs.
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿豈-﫿！-￯]")


def _text(content: bytes) -> str:
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
    return re.sub(r"[\s　]+", " ", text)


def _unwritten_japanese(text: str, written: list[str]) -> list[str]:
    """Japanese left once the user's words and the form's are taken away.

    Longest first, so a value containing another is removed whole.
    """
    for value in sorted({*written, *FORM}, key=len, reverse=True):
        text = text.replace(value, " ")
    text = DATE.sub(" ", text)
    return JAPANESE.findall(text)


def _generate(client, auth_headers, body: dict | None = None) -> str:
    response = client.post(PATH, headers=auth_headers, json=body or {})
    assert response.status_code == 200, response.text
    return _text(response.content)


@pytest.fixture
def english_profile(session, user_id):
    """Everything written in English, as a user new to Japan might."""
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Maria Santos",
            date_of_birth=date(1994, 2, 3),
            address="2-1 Example Street, Shibuya, Tokyo",
            email="maria@example.com",
        )
    )
    session.add(
        models.Education(
            profile_id=profile.id,
            institution="University of the Example",
            qualification="BSc Computer Science",
            started_on=date(2012, 6, 1),
            ended_on=date(2016, 4, 30),
        )
    )
    session.add(
        models.WorkExperience(
            profile_id=profile.id,
            employer_name="Example Corp",
            employer_name_normalised="example",
            job_title="Software Engineer",
            started_on=date(2016, 7, 1),
            source_language=models.Locale.en,
        )
    )
    session.flush()
    return profile


ENGLISH_VALUES = [
    "Maria Santos",
    "2-1 Example Street, Shibuya, Tokyo",
    "maria@example.com",
    "University of the Example",
    "Example Corp",
]


class TestEnglishAppearsAsWritten:
    @pytest.mark.parametrize("value", ENGLISH_VALUES)
    def test_each_english_value_appears_exactly(self, client, auth_headers, english_profile, value):
        assert value in _generate(client, auth_headers)

    def test_each_english_entry_appears_once_per_row(self, client, auth_headers, english_profile):
        """Scenario 5's own check: not duplicated beside a translation.

        Education has a row for entering and one for leaving; an ongoing role
        has one for joining, and 現在に至る carries no name.
        """
        text = _generate(client, auth_headers)
        assert text.count("Example Corp") == 1
        assert text.count("University of the Example") == 2
        assert "University of the Example 入学" in text
        assert "University of the Example 卒業" in text

    def test_an_english_entry_among_japanese_ones_stays_english(
        self, client, auth_headers, rirekisho_profile
    ):
        """The shared fixture's second role was written in English."""
        assert "Example Corp" in _generate(client, auth_headers)


class TestNoJapaneseTheUserDidNotWrite:
    @pytest.mark.parametrize(
        "body",
        [{}, {"date_convention": "wareki"}, {"paper_size": "b5"}],
        ids=["default", "wareki", "b5"],
    )
    def test_an_english_profile_gains_only_the_forms_japanese(
        self, client, auth_headers, english_profile, body
    ):
        text = _generate(client, auth_headers, body)
        assert _unwritten_japanese(text, ENGLISH_VALUES) == []

    def test_a_mixed_profile_gains_only_the_forms_japanese(
        self, client, auth_headers, rirekisho_profile
    ):
        written = [
            "山田太郎",
            "ヤマダタロウ",
            "東京都新宿区サンプル1-2-3",
            "サンプル大学",
            "株式会社サンプル",
            "Example Corp",
        ]
        text = _generate(client, auth_headers, {"date_convention": "wareki"})
        assert _unwritten_japanese(text, written) == []

    def test_the_subtraction_would_see_an_invented_translation(self):
        """Guards the guard: a translation left in the text is found."""
        text = "学歴・職歴 2016年7月 Example Corp 入社 エグザンプル株式会社 以上"
        assert _unwritten_japanese(text, ["Example Corp"]) != []
