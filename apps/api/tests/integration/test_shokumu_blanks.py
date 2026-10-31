"""Quickstart Scenario 5 — a thin profile produces a thin document.

The failure this guards against is the helpful one. A generator with nothing
to say about an employer is one line of code away from saying something
anyway: a sample description, an inferred responsibility, a heading quietly
dropped because it had nothing under it. Each reads well and none of it is
true, and the person who signs the document is the one who carries that.

So the main test here enumerates. A blocklist of known placeholders only
catches the placeholders someone thought of; a thin profile's document is
short enough to write out in full, so it is written out in full and compared.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"


@pytest.fixture
def bare_profile(session, user_id):
    """A name, and one employer with a name and a start date. Nothing else.

    No job description, no employment type, no end date, no achievements, no
    skills, no languages, no certifications — every optional thing the
    document has a section for is absent.
    """
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
    session.add(
        models.WorkExperience(
            profile_id=profile.id,
            employer_name="株式会社サンプル",
            employer_name_normalised="サンプル",
            job_title="エンジニア",
            started_on=date(2020, 4, 1),
        )
    )
    session.flush()
    return profile


def _lines(client, auth_headers, **body) -> list[str]:
    response = client.post(PATH, headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(response.content)).pages)
    return [line.strip() for line in text.splitlines() if line.strip()]


class TestTheWholeDocument:
    def test_a_bare_profile_produces_exactly_these_lines(self, client, auth_headers, bare_profile):
        """Enumerated rather than searched. Anything the generator adds —
        a sample, an inferred responsibility, a helpful note — fails here
        whether or not anyone predicted it."""
        today = date.today()
        years = today.year - 2020 - ((today.month, today.day) < (4, 1))

        assert _lines(client, auth_headers) == [
            "職務経歴書",
            "氏名　Taro Yamada",
            f"作成日　{today.year}年{today.month}月{today.day}日",
            "職務要約",
            f"職務経験年数　{years}年（2020年4月〜現在）",
            "在籍企業数　1社",
            "直近の職務　株式会社サンプル　エンジニア",
            "職務経歴",
            "株式会社サンプル",
            "期間　2020年4月〜現在",
            "職種　エンジニア",
            "活かせる経験・知識・技術",
            "語学",
            "免許・資格",
            "自己PR",
            "以上",
        ]

    def test_an_employer_with_no_description_gets_no_narrative(
        self, client, auth_headers, bare_profile
    ):
        """Said separately from the list above, because this is the line most
        likely to be added by someone being helpful."""
        lines = _lines(client, auth_headers)
        role = lines.index("職種　エンジニア")
        between = lines[role + 1 : lines.index("活かせる経験・知識・技術")]
        assert between == [], f"something was written for an employer that said nothing: {between}"

    def test_an_empty_section_keeps_its_heading(self, client, auth_headers, bare_profile):
        """FR-014: a blank reads as a decision rather than as a defect. The
        heading is how the user can see that the product looked and found
        nothing, rather than never having a place for it."""
        lines = _lines(client, auth_headers)
        for heading in ("活かせる経験・知識・技術", "語学", "免許・資格"):
            assert heading in lines

    def test_an_empty_section_has_nothing_under_it(self, client, auth_headers, bare_profile):
        lines = _lines(client, auth_headers)
        order = ["活かせる経験・知識・技術", "語学", "免許・資格", "自己PR"]
        for heading, next_heading in zip(order, order[1:], strict=False):
            assert lines.index(next_heading) == lines.index(heading) + 1


class TestSelfPromotion:
    """FR-020 — 自己PR is the user's to write, in every document."""

    @pytest.mark.parametrize("convention", ["seireki", "wareki"])
    @pytest.mark.parametrize("paper", ["a4", "b5"])
    def test_it_is_labelled_and_empty_whatever_was_asked_for(
        self, client, auth_headers, shokumu_profile, convention, paper
    ):
        lines = _lines(client, auth_headers, date_convention=convention, paper_size=paper)
        assert lines[lines.index("自己PR") + 1 :] == ["以上"]

    def test_it_is_there_even_for_a_profile_with_almost_nothing(
        self, client, auth_headers, bare_profile
    ):
        lines = _lines(client, auth_headers)
        assert lines[lines.index("自己PR") + 1 :] == ["以上"]

    def test_it_is_there_even_for_a_profile_with_a_great_deal(
        self, client, auth_headers, shokumu_profile
    ):
        assert "自己PR" in _lines(client, auth_headers)


class TestNoJapanSpecificField:
    """Gate G5 holds here by exclusion, and this is what proves it.

    A 職務経歴書 is a career history, not a personal-details form, so this
    feature never reads `JapanProfile` at all. A guarantee by absence is the
    easiest kind to lose: someone adds a field, nothing objects, and an
    immigration status reaches an employer who was never shown it in the
    document the user chose to disclose it in.

    So every flag is opened here. Consent given for the 履歴書 is not consent
    for this document, and the test asserts on that rather than on the
    default of everything being closed.
    """

    VALUES = {
        "residence_status": "永住者",
        "nationality": "Philippines",
        "visa_type": "技術・人文知識・国際業務",
        "visa_expires_on": date(2028, 3, 31),
        "work_authorisation": True,
        "japanese_qualification": "JLPT N2",
    }

    LABELS = ("在留資格", "国籍", "ビザ", "在留期限", "就労資格", "日本語能力")

    @pytest.fixture
    def disclosed(self, session, shokumu_profile):
        from app.career import models

        record = models.JapanProfile(
            profile_id=shokumu_profile.id,
            **self.VALUES,
            disclose_residence_status=True,
            disclose_nationality=True,
            disclose_visa=True,
            disclose_work_authorisation=True,
            disclose_japanese_qualification=True,
        )
        session.add(record)
        session.flush()
        return record

    def test_no_disclosed_value_reaches_the_document(self, client, auth_headers, disclosed):
        document = "".join(_lines(client, auth_headers))
        for field, value in self.VALUES.items():
            if isinstance(value, str):
                assert value not in document, f"{field} reached a 職務経歴書"

    def test_no_label_reaches_it_either(self, client, auth_headers, disclosed):
        """A blank 国籍 line still tells a reader there is one being withheld."""
        document = "".join(_lines(client, auth_headers))
        for label in self.LABELS:
            assert label not in document

    def test_the_date_of_a_visa_is_not_there_in_either_calendar(
        self, client, auth_headers, disclosed
    ):
        for convention in ("seireki", "wareki"):
            document = "".join(_lines(client, auth_headers, date_convention=convention))
            assert "2028" not in document
            assert "令和10年3月" not in document

    def test_the_fixture_really_did_disclose_everything(self, disclosed):
        """Otherwise the tests above pass on a profile that disclosed nothing."""
        from app.rirekisho.disclosure import disclosed_fields

        assert set(disclosed_fields(disclosed)) == set(self.VALUES)


class TestNothingIsAddedByTheConventions:
    @pytest.mark.parametrize("convention", ["seireki", "wareki"])
    def test_a_bare_document_has_the_same_shape_in_either_calendar(
        self, client, auth_headers, bare_profile, convention
    ):
        """Changing the calendar changes the dates and nothing else."""
        lines = _lines(client, auth_headers, date_convention=convention)
        without_dates = [re.sub(r"[0-9]+|令和|平成|昭和", "", line) for line in lines]

        seireki = [
            re.sub(r"[0-9]+|令和|平成|昭和", "", line)
            for line in _lines(client, auth_headers, date_convention="seireki")
        ]
        assert without_dates == seireki
