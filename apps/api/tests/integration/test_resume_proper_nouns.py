"""Quickstart Scenario 17 — a name is not a thing to translate (FR-021, R-002).

株式会社サンプル's English name is whatever that company calls itself. There
is no way to work it out from the Japanese, and a transliteration is a guess
the applicant would have to answer for — so the user supplies it or the
Japanese stands on the page, which is why an English resume still embeds a
CJK font.

The same reasoning, one step further, is why a certification is not a
translatable entry type at all. It holds a name, an issuer and two dates:
the first two are proper nouns and the last two are not words. There is
nothing on one a model could draft without inventing it, so the drafting
route refuses the type rather than offering a suggestion nobody should
accept.
"""

import io
import re
from collections.abc import Iterable

import pytest
from app.documents.dates import MONTHS
from pypdf import PdfReader

RESUME = "/api/v1/profile/documents/resume"
READINESS = "/api/v1/profile/documents/resume/readiness"
DRAFTS = "/api/v1/profile/translations/drafts"

RECORDED_EMPLOYER = "株式会社サンプル"
SUPPLIED_EMPLOYER = "合同会社テスト"
SUPPLIED_ENGLISH = "Test LLC"
CERTIFICATION = "基本情報技術者"
ISSUER = "情報処理推進機構"


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def _lines(text: str) -> list[str]:
    return [line for line in (raw.strip() for raw in text.splitlines()) if line]


#: A month and its year together, as `format_month` writes them, with the
#: month names taken from the renderer rather than written out again here.
#:
#: Together, and never a month on its own. A bare three-letter word is as
#: likely to be a name nobody supplied as it is to be April — `IPA` is the
#: English name of 情報処理推進機構, the issuer this file exists to prove
#: was never invented, and a rule that discarded any three letters followed
#: by a space would discard the leak along with the date.
DATE = re.compile(rf"(?:{'|'.join(MONTHS)})\s+\d{{4}}")


def _unaccounted(line: str, names: Iterable[str]) -> str:
    """What is left of a line once the names that belong on it are removed.

    A date and the separators the renderer puts between fields are the
    document speaking. Everything else is text nobody supplied, and on a
    line of proper nouns that means something was invented.
    """
    remainder = line
    for name in names:
        remainder = remainder.replace(name, "")
    remainder = DATE.sub("", remainder)
    return re.sub(r"[–—\-,.()\s]", "", remainder)


@pytest.fixture
def proper_nouns(session, user_id):
    """Two employers and a certification, in Japanese.

    One employer has an English name supplied and one does not, because the
    two have to be told apart: a product that printed the Japanese for both
    would pass a test that only looked for 株式会社サンプル.
    """
    from datetime import date

    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
    session.add_all(
        [
            models.WorkExperience(
                profile_id=profile.id,
                employer_name=RECORDED_EMPLOYER,
                employer_name_normalised="サンプル",
                job_title="Software Engineer",
                started_on=date(2015, 4, 1),
                ended_on=date(2021, 3, 31),
                description="Platform work.",
                source_language=models.Locale.en,
            ),
            models.WorkExperience(
                profile_id=profile.id,
                employer_name=SUPPLIED_EMPLOYER,
                employer_name_english=SUPPLIED_ENGLISH,
                employer_name_normalised="テスト",
                job_title="Engineer",
                started_on=date(2021, 4, 1),
                ended_on=None,
                description="Platform work.",
                source_language=models.Locale.en,
            ),
            models.Certification(
                profile_id=profile.id,
                name=CERTIFICATION,
                issuer=ISSUER,
                issued_on=date(2014, 4, 1),
            ),
        ]
    )
    session.flush()
    return profile


@pytest.fixture
def document(client, auth_headers, proper_nouns):
    response = client.post(RESUME, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return _text(response.content)


@pytest.fixture
def report(client, auth_headers, proper_nouns):
    response = client.get(READINESS, headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()


class TestWhatThePageCarries:
    def test_an_employer_with_no_english_name_appears_as_recorded(self, document):
        assert RECORDED_EMPLOYER in document

    def test_an_employer_with_one_appears_in_english(self, document):
        """And not alongside the Japanese. A resume that printed both would
        be making the reader do the matching."""
        assert SUPPLIED_ENGLISH in document
        assert SUPPLIED_EMPLOYER not in document

    def test_a_certification_and_its_issuer_appear_as_recorded(self, document):
        """The issuer especially. It is the proper noun an applicant would
        have to answer for — who says you hold this — and an invented
        English form of it is a claim about a body that never made one."""
        assert CERTIFICATION in document
        assert ISSUER in document

    def test_the_unsupplied_names_stand_alone_on_their_lines(self, document):
        """The oracle for "nothing was transliterated", and it does not
        depend on guessing what a transliteration would have looked like.

        Each of these names is recorded in Japanese with no English form
        supplied, so the only text that may accompany it on the page is the
        document's own — a job title, a date, a separator. Anything else in
        Latin letters beside it is a name nobody gave us.
        """
        for recorded, allowed in (
            (RECORDED_EMPLOYER, {"Software Engineer"}),
            # The two share a line: a certification prints as its name,
            # its issuer and the date it was awarded.
            (CERTIFICATION, {ISSUER}),
            (ISSUER, {CERTIFICATION}),
        ):
            line = next(line for line in _lines(document) if recorded in line)
            remainder = _unaccounted(line, (recorded, *allowed))
            assert remainder == "", f"{recorded} shares its line with {remainder!r}"

    def test_the_oracle_reports_a_name_nobody_supplied(self):
        """What the assertion above is worth, asked of the oracle directly.

        `IPA` is the English name of 情報処理推進機構 and no one gave it to
        us. A reading of the line that threw those three letters away as a
        month would let exactly the invention this file is about through,
        and would do it silently.
        """
        invented = f"{CERTIFICATION} – {ISSUER} IPA – Apr 2014"

        assert _unaccounted(invented, (CERTIFICATION, ISSUER)) == "IPA"

    def test_the_oracle_passes_the_line_the_renderer_writes(self):
        """The other half: a real line has to come back empty, or the test
        above is satisfied by an oracle that reports everything."""
        written = f"{CERTIFICATION} – {ISSUER} – Apr 2014"

        assert _unaccounted(written, (CERTIFICATION, ISSUER)) == ""


class TestWhatTheReportSays:
    def test_the_unnamed_employer_is_listed(self, report):
        names = {
            (item["entry_type"], item["recorded_name"]) for item in report["untranslated_names"]
        }
        assert ("work_experience", RECORDED_EMPLOYER) in names

    def test_the_certification_contributes_both_its_names(self, report):
        """A certification has two — the award and the body that gave it —
        and `field` on the report is what tells them apart."""
        fields = {
            item["field"]
            for item in report["untranslated_names"]
            if item["entry_type"] == "certification"
        }
        assert fields == {"name", "issuer"}

    def test_the_employer_whose_name_was_supplied_is_not_listed(self, report):
        recorded = {item["recorded_name"] for item in report["untranslated_names"]}
        assert SUPPLIED_EMPLOYER not in recorded

    def test_none_of_them_is_listed_as_needing_english(self, report):
        """`needs_english` is the list with a draft button beside it. A name
        on it would invite exactly the guess FR-021 forbids."""
        recorded = {item["source_text"] for item in report["needs_english"]}
        assert RECORDED_EMPLOYER not in recorded
        assert CERTIFICATION not in recorded
        assert ISSUER not in recorded

    def test_the_report_still_says_the_document_can_be_made(self, report):
        """None of this blocks anything. The Japanese goes on the page and
        the user is told (FR-017)."""
        assert report["can_generate"] is True


class TestACertificationCannotBeDrafted:
    def test_the_type_is_refused(self, client, auth_headers, session, proper_nouns):
        from app.career.models import Certification
        from sqlalchemy import select

        entry = session.scalars(
            select(Certification).where(Certification.profile_id == proper_nouns.id)
        ).one()

        response = client.post(
            DRAFTS,
            headers=auth_headers,
            json={"entry_type": "certification", "entry_id": str(entry.id), "field": "name"},
        )

        assert response.status_code == 422, response.text
        failures = response.json()["failures"]
        assert [item["field"] for item in failures] == ["entry_type"]
        # The reason names what may be drafted, so a user reading it is not
        # left guessing which of the four this was supposed to be.
        assert "certification" not in failures[0]["reason"]
        for allowed in ("work_experience", "education", "career_story", "skill"):
            assert allowed in failures[0]["reason"]

    def test_a_type_that_can_be_drafted_gets_past_the_same_check(
        self, client, auth_headers, session, proper_nouns
    ):
        """The refusal above has to be about the type and not about the
        route being broken for everything.

        This one is refused too — the title is already in English, and the
        drafts route will not invite a model to improve someone's wording —
        but it is refused for a different reason, and the reason is the
        thing under test.
        """
        from app.career.models import WorkExperience
        from sqlalchemy import select

        entry = session.scalars(
            select(WorkExperience).where(
                WorkExperience.profile_id == proper_nouns.id,
                WorkExperience.employer_name == RECORDED_EMPLOYER,
            )
        ).one()

        response = client.post(
            DRAFTS,
            headers=auth_headers,
            json={"entry_type": "work_experience", "entry_id": str(entry.id), "field": "job_title"},
        )

        assert response.status_code == 422, response.text
        failures = response.json()["failures"]
        assert [item["field"] for item in failures] == ["field"]
        assert "already in English" in failures[0]["reason"]

    def test_an_employer_name_is_not_a_field_that_can_be_drafted(
        self, client, auth_headers, session, proper_nouns
    ):
        """The other way in. `work_experience` is a translatable type, and
        `employer_name` is still a proper noun on it."""
        from app.career.models import WorkExperience
        from sqlalchemy import select

        entry = session.scalars(
            select(WorkExperience).where(
                WorkExperience.profile_id == proper_nouns.id,
                WorkExperience.employer_name == RECORDED_EMPLOYER,
            )
        ).one()

        response = client.post(
            DRAFTS,
            headers=auth_headers,
            json={
                "entry_type": "work_experience",
                "entry_id": str(entry.id),
                "field": "employer_name",
            },
        )

        assert response.status_code == 422, response.text
        failures = response.json()["failures"]
        assert [item["field"] for item in failures] == ["field"]
        # Named rather than matched loosely: "refused" is also what a
        # broken route looks like, and the three refusals in this class
        # have to be told apart.
        assert failures[0]["reason"] == (
            "work_experience has no translatable field 'employer_name'"
        )
