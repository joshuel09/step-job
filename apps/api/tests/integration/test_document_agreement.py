"""Quickstart Scenario 8 — the two documents agree (FR-018).

The scenario unique to feature 004, and the one failure an employer would
find first and nobody else would find at all. A 履歴書 and a 職務経歴書 are
often sent together. If they disagree about when someone joined a company,
the reader does not conclude that a date formatter drifted; they conclude
that the applicant is careless with facts, or worse.

Nothing compares the two at generation time. They agree because both are
assembled from the same entries by the same date and ordering code
(research.md R-006), and that is the mechanism. This test is what would
catch that shared code diverging — the day someone changes an era table, a
wrapping rule or a sort in one renderer and not the other.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader

RIREKISHO = "/api/v1/profile/documents/rirekisho"
SHOKUMU = "/api/v1/profile/documents/shokumu-keirekisho"

EMPLOYERS = [
    ("株式会社サンプル", "エンジニア", date(2013, 4, 1), date(2018, 3, 31)),
    ("Example Corp", "Software Engineer", date(2018, 4, 1), date(2021, 3, 31)),
    ("合同会社テスト", "主任", date(2021, 4, 1), None),
]


@pytest.fixture
def shared_profile(session, user_id):
    """One profile, enough to fill both documents."""
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
            started_on=date(2009, 4, 1),
            ended_on=date(2013, 3, 31),
        )
    )
    for name, title, started, ended in EMPLOYERS:
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name=name,
                employer_name_normalised=name.lower(),
                job_title=title,
                started_on=started,
                ended_on=ended,
            )
        )
    session.add(
        models.Certification(
            profile_id=profile.id, name="基本情報技術者", issued_on=date(2014, 4, 1)
        )
    )
    session.flush()
    return profile


def _pdf(client, auth_headers, path: str, **body) -> bytes:
    response = client.post(path, headers=auth_headers, json=body)
    assert response.status_code == 200, f"{path}: {response.text}"
    return response.content


def _squash(text: str) -> str:
    return re.sub(r"[\s　]+", "", text)


def _lines(pdf: bytes) -> list[str]:
    return [
        line.strip()
        for page in PdfReader(io.BytesIO(pdf)).pages
        for line in (page.extract_text() or "").splitlines()
        if line.strip()
    ]


def _both(client, auth_headers, **body) -> tuple[str, str]:
    return tuple(
        _squash("".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages))
        for pdf in (
            _pdf(client, auth_headers, RIREKISHO, **body),
            _pdf(client, auth_headers, SHOKUMU, **body),
        )
    )


def _rirekisho_dates(pdf: bytes, employer: str) -> str:
    """Every row of the 学歴・職歴 table that names this employer, joined.

    The table draws one row per event — joining and leaving — each beginning
    with its own date, so the dates belonging to an employer are the ones on
    that employer's own rows and nowhere else.
    """
    wanted = _squash(employer)
    return "".join(_squash(line) for line in _lines(pdf) if wanted in _squash(line))


def _shokumu_period(pdf: bytes, employer: str) -> str:
    """The 期間 line of this employer's own section.

    The heading is the employer's name on a line of its own, and the period
    is the line under it. Reading it this way is what makes a period swapped
    between two employers visible.
    """
    lines = _lines(pdf)
    wanted = _squash(employer)
    for number, line in enumerate(lines):
        if _squash(line) == wanted:
            following = _squash(lines[number + 1]) if number + 1 < len(lines) else ""
            assert following.startswith("期間"), f"{employer} has no period under it: {following}"
            return following
    raise AssertionError(f"{employer} has no section of its own")


CONVENTIONS = pytest.mark.parametrize("convention", ["seireki", "wareki"])


@CONVENTIONS
class TestTheyAgreeOnEveryFactBothCarry:
    def test_on_the_name(self, client, auth_headers, shared_profile, convention):
        rirekisho, shokumu = _both(client, auth_headers, date_convention=convention)
        assert "山田太郎" in rirekisho
        assert "山田太郎" in shokumu

    def test_on_every_employer(self, client, auth_headers, shared_profile, convention):
        rirekisho, shokumu = _both(client, auth_headers, date_convention=convention)
        for name, _, _, _ in EMPLOYERS:
            squashed = re.sub(r"\s+", "", name)
            assert squashed in rirekisho, f"{name} is missing from the 履歴書"
            assert squashed in shokumu, f"{name} is missing from the 職務経歴書"

    def test_on_every_date_both_documents_print(
        self, client, auth_headers, shared_profile, convention
    ):
        """The sharpest of these. Both write a period for each employer, and
        both get it from `format_year_month`. A change to the era table in
        one renderer and not the other shows up here and nowhere else.

        Checked against the employer it belongs to, not against the document
        as a whole: two employers with their periods swapped carry every one
        of these dates somewhere, and contradict each other anyway.
        """
        from app.imports.dates import format_year_month

        era = convention == "wareki"
        rirekisho = _pdf(client, auth_headers, RIREKISHO, date_convention=convention)
        shokumu = _pdf(client, auth_headers, SHOKUMU, date_convention=convention)

        for name, _, started, ended in EMPLOYERS:
            rows = _rirekisho_dates(rirekisho, name)
            period = _shokumu_period(shokumu, name)

            for when in (started, ended):
                if when is None:
                    continue
                written = format_year_month(when, era=era)
                assert written in rows, f"{name}: {written} is not on its 履歴書 rows"
                assert written in period, f"{name}: {written} is not in its 職務経歴書 period"

    def test_a_date_belonging_to_another_employer_is_not_on_this_one(
        self, client, auth_headers, shared_profile, convention
    ):
        """What the assertion above is for. Every date in this profile
        appears in both documents; only the pairing can be wrong."""
        from app.imports.dates import format_year_month

        era = convention == "wareki"
        shokumu = _pdf(client, auth_headers, SHOKUMU, date_convention=convention)

        first, second = EMPLOYERS[0], EMPLOYERS[1]
        theirs = format_year_month(second[2], era=era)
        assert theirs not in _shokumu_period(shokumu, first[0]), (
            f"{first[0]} carries {second[0]}'s start date"
        )

    def test_on_an_ongoing_role(self, client, auth_headers, shared_profile, convention):
        """Both say the role continues. They say it in their own words — a
        履歴書 writes 現在に至る in its table and a 職務経歴書 writes 現在 at
        the end of a period — but neither invents an end date."""
        rirekisho, shokumu = _both(client, auth_headers, date_convention=convention)
        assert "現在に至る" in rirekisho
        assert "現在" in shokumu

    def test_neither_invents_an_end_for_it(self, client, auth_headers, shared_profile, convention):
        from app.imports.dates import format_year_month

        rirekisho, shokumu = _both(client, auth_headers, date_convention=convention)
        # The ongoing role started in 2021-04 and has no end. Any later date
        # in either document would be one the profile does not hold.
        invented = format_year_month(date(2026, 4, 1), era=(convention == "wareki"))
        assert invented not in rirekisho
        assert invented not in shokumu


@CONVENTIONS
def test_one_calendar_across_both_documents(client, auth_headers, shared_profile, convention):
    """A pair sent together must not be in two calendars.

    Each document holds to one convention on its own; this is the check that
    the choice reaches both of them.
    """
    rirekisho, shokumu = _both(client, auth_headers, date_convention=convention)
    eras = ("令和", "平成", "昭和")

    for document in (rirekisho, shokumu):
        if convention == "wareki":
            assert re.findall(r"(?<!\d)\d{4}(?!\d)", document) == []
            assert any(era in document for era in eras)
        else:
            assert [era for era in eras if era in document] == []


class TestWhatOnlyOneOfThemCarries:
    def test_the_履歴書_carries_education_and_the_other_does_not(
        self, client, auth_headers, shared_profile
    ):
        """Not a disagreement: a 職務経歴書 is work history. Stated so that
        the agreement tests above are not read as "the two are the same"."""
        rirekisho, shokumu = _both(client, auth_headers)
        assert "サンプル大学" in rirekisho
        assert "サンプル大学" not in shokumu

    def test_the_履歴書_carries_a_date_of_birth_and_the_other_does_not(
        self, client, auth_headers, shared_profile
    ):
        rirekisho, shokumu = _both(client, auth_headers)
        assert "1990年5月15日" in rirekisho
        assert "1990" not in shokumu

    def test_they_still_agree_on_the_job_titles(self, client, auth_headers, shared_profile):
        """The 履歴書's table names employers rather than roles, so the
        titles live only in the 職務経歴書 — which means there is nothing to
        disagree about, and this records that rather than asserting it."""
        _, shokumu = _both(client, auth_headers)
        for _, title, _, _ in EMPLOYERS:
            assert re.sub(r"\s+", "", title) in shokumu
