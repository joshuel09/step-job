"""Quickstart Scenario 8, and feature 005's Scenario 15 — the documents agree.

Feature 004, FR-018: a 履歴書 and a 職務経歴書 are often sent together.
Feature 005 adds a third reader of the same profile, and the gap it has to
cross is wider — one document is in Japanese and dated 年月, the other is in
English and dated Apr 2013.

This is the one failure an employer would find first and nobody else would
find at all. If two documents from one profile disagree about when someone
joined a company, the reader does not conclude that a date formatter
drifted; they conclude that the applicant is careless with facts, or worse.

What may differ is the wording. The Japanese documents print 主任 and the
resume prints whatever English the user approved for it — that is the
product working, not a disagreement (R-008), and the comparison is made
over employers and periods for exactly that reason.

Nothing compares them at generation time. They agree because both are
assembled from the same entries by the same date and ordering code
(research.md R-006), and that is the mechanism. This test is what would
catch that shared code diverging — the day someone changes an era table, a
wrapping rule or a sort in one renderer and not the other.
"""

import io
import re
from datetime import date, datetime

import pytest
from pypdf import PdfReader

RIREKISHO = "/api/v1/profile/documents/rirekisho"
RESUME = "/api/v1/profile/documents/resume"
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


# --- feature 005: and the English resume agrees with both -------------------


def _resume_period(pdf: bytes, employer: str) -> str:
    """The period under this employer's own entry.

    A resume writes "Title – Employer" and the period on the line beneath,
    so the period belonging to an employer is the one under that employer's
    line. Read this way rather than off the document as a whole, because two
    roles with their periods swapped carry every date somewhere.
    """
    lines = _lines(pdf)
    wanted = _squash(employer)
    for number, line in enumerate(lines):
        if _squash(line).endswith(wanted):
            assert number + 1 < len(lines), f"{employer} has no line under it"
            return lines[number + 1]
    raise AssertionError(f"{employer} is not on the resume")


def _months(period: str) -> list[tuple[int, int] | None]:
    """A written period as the year and month it names.

    Compared as dates rather than as strings, which is the whole point of
    this file: the two documents write the same month in different scripts,
    and the comparison has to see past that. `None` is an ongoing role,
    never an unknown date.
    """
    out: list[tuple[int, int] | None] = []
    for part in re.split(r"[–—-]", period):
        part = part.strip()
        if not part:
            continue
        if part.lower() == "present":
            out.append(None)
            continue
        when = datetime.strptime(part, "%b %Y")
        out.append((when.year, when.month))
    return out


class TestTheResumeAgreesWithTheRirekisho:
    """Quickstart Scenario 15 — the third document joins the agreement.

    The same two guarantees as above, across a harder gap: one document is
    in Japanese and dated 年月, the other is in English and dated Apr 2013.
    What must match is who the applicant worked for and when — never the
    wording, which is the product working rather than a disagreement
    (research.md R-008).
    """

    def test_every_employer_is_on_both(self, client, auth_headers, shared_profile):
        rirekisho = _squash(
            "".join(
                page.extract_text() or ""
                for page in PdfReader(io.BytesIO(_pdf(client, auth_headers, RIREKISHO))).pages
            )
        )
        resume = _lines(_pdf(client, auth_headers, RESUME))

        for name, _, _, _ in EMPLOYERS:
            assert _squash(name) in rirekisho, f"{name} is missing from the 履歴書"
            assert any(_squash(name) in _squash(line) for line in resume), (
                f"{name} is missing from the resume"
            )

    def test_each_employer_keeps_its_own_period(self, client, auth_headers, shared_profile):
        """The sharpest of these, and the one a reader would catch first:
        two documents from one profile that disagree about when someone
        joined a company do not read as a formatting bug.

        Both sides are compared against the dates in `EMPLOYERS`, written
        out here rather than through `format_year_month`. That function is
        what puts the date on the 履歴書; asking it what the date should be
        would make a change to it agree with itself.
        """
        rirekisho = _pdf(client, auth_headers, RIREKISHO)
        resume = _pdf(client, auth_headers, RESUME)

        for name, _, started, ended in EMPLOYERS:
            recorded = [
                (started.year, started.month),
                None if ended is None else (ended.year, ended.month),
            ]
            assert _months(_resume_period(resume, name)) == recorded, name

            rows = _rirekisho_dates(rirekisho, name)
            for when in (started, ended):
                if when is not None:
                    assert f"{when.year}年{when.month}月" in rows, f"{name}: {when}"

    def test_a_period_belonging_to_another_employer_is_not_on_this_one(
        self, client, auth_headers, shared_profile
    ):
        """What the assertion above is for. Every date in this profile is on
        the resume somewhere; only the pairing can be wrong."""
        resume = _pdf(client, auth_headers, RESUME)
        first, second = EMPLOYERS[0], EMPLOYERS[1]

        assert (second[2].year, second[2].month) not in _months(_resume_period(resume, first[0]))

    def test_an_ongoing_role_is_open_on_both(self, client, auth_headers, shared_profile):
        """Each says it in its own convention — 現在に至る on a row of its own
        in a 履歴書's table and Present at the end of a period on a resume —
        and neither invents an end date to fill the space.

        Tied to the employer on both sides. 現在に至る found anywhere in the
        document would be satisfied by a 履歴書 that marked the wrong role
        as continuing, which is a worse error than not marking one at all.
        """
        rirekisho = _pdf(client, auth_headers, RIREKISHO)
        resume = _pdf(client, auth_headers, RESUME)
        ongoing, *_ = EMPLOYERS[2]

        lines = _lines(rirekisho)
        rows = [n for n, line in enumerate(lines) if _squash(ongoing) in _squash(line)]

        # Both of these would otherwise be a bare ValueError or IndexError
        # out of the line below — a failure that says the test broke rather
        # than that the employer never reached the document.
        assert rows, f"{ongoing} is not on the 履歴書 at all"
        assert rows[-1] + 1 < len(lines), f"{ongoing} is the last line, with no row under it"

        assert _squash(lines[rows[-1] + 1]) == "現在に至る"
        assert "退社" not in _rirekisho_dates(rirekisho, ongoing)
        assert _months(_resume_period(resume, ongoing))[-1] is None

    def test_a_finished_role_is_closed_on_both(self, client, auth_headers, shared_profile):
        """The other half of the same statement, and what makes the one
        above mean something: the roles that ended say so."""
        rirekisho = _pdf(client, auth_headers, RIREKISHO)
        resume = _pdf(client, auth_headers, RESUME)

        for name, _, _, ended in EMPLOYERS[:2]:
            assert "退社" in _rirekisho_dates(rirekisho, name), name
            assert _months(_resume_period(resume, name))[-1] == (ended.year, ended.month), name


class TestWhatIsAllowedToDiffer:
    """And the thing that must not be mistaken for a disagreement.

    An approved English title is the applicant's own rendering of their
    Japanese one. The two documents then carry different words for the same
    role, deliberately: a 履歴書 is read in Japanese and a resume is not, and
    making them say the same string would mean printing one of the two in
    the wrong language (R-008).
    """

    @pytest.fixture
    def approved(self, session, shared_profile):
        """An English title for the ongoing 主任 role."""
        from datetime import UTC
        from datetime import datetime as dt

        from app.career.models import Locale, WorkExperience
        from app.translations.models import EntryTranslation, TranslatableEntry
        from sqlalchemy import select

        entry = session.scalars(
            select(WorkExperience).where(
                WorkExperience.profile_id == shared_profile.id,
                WorkExperience.employer_name == "合同会社テスト",
            )
        ).one()
        session.add(
            EntryTranslation(
                profile_id=shared_profile.id,
                entry_type=TranslatableEntry.work_experience,
                entry_id=entry.id,
                field="job_title",
                language=Locale.en,
                approved_text="Section Chief",
                approved_at=dt.now(UTC),
                source_fingerprint="0" * 64,
            )
        )
        session.flush()
        return entry

    def test_the_resume_carries_the_english_the_user_approved(
        self, client, auth_headers, shared_profile, approved
    ):
        resume = _lines(_pdf(client, auth_headers, RESUME))

        assert any("Section Chief" in line for line in resume)
        assert not any("主任" in line for line in resume)

    def test_and_the_periods_still_agree(self, client, auth_headers, shared_profile, approved):
        """The title changed; the facts did not. This is what separates a
        rendering from a disagreement."""
        name, _, started, _ = EMPLOYERS[2]
        rirekisho = _pdf(client, auth_headers, RIREKISHO)
        resume = _pdf(client, auth_headers, RESUME)

        assert _months(_resume_period(resume, name))[0] == (started.year, started.month)
        assert f"{started.year}年{started.month}月" in _rirekisho_dates(rirekisho, name)
