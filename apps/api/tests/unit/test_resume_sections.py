"""The profile projected into what an English resume may show.

The order and the fallbacks are ordinary tests. `TestWhatTheRendererCannotBeGiven`
is not: it is the mechanism FR-009 and FR-010 rest on, written as a test
because the mechanism is an absence and an absence is the easiest thing in a
codebase to reintroduce by accident.

The forbidden names are read off `JapanProfile` rather than listed here. A
list of three would keep passing on the day someone adds a fourth column to
that table, which is the day it would need to fail.
"""

import dataclasses
import uuid
from datetime import UTC, date, datetime

import pytest
from app.career.models import JapanProfile, Locale
from app.resume.sections import (
    CertificationEntry,
    Contact,
    EducationEntry,
    ExperienceEntry,
    ResumeContent,
    SkillEntry,
    build_content,
)
from app.translations.models import EntryTranslation, TranslatableEntry


class _Row:
    """A stand-in for an ORM row, so these stay unit tests.

    The projection takes anything with the right attributes — it is a pure
    function over entries, and giving it a session would be the first step
    towards it growing a query.
    """

    def __init__(self, **fields):
        self.id = fields.pop("id", uuid.uuid4())
        for name, value in fields.items():
            setattr(self, name, value)


def _identity(**overrides):
    return _Row(
        **{
            "full_name_latin": "Example Person",
            "email": "example@example.com",
            "phone": "090-0000-0000",
            **overrides,
        }
    )


def _experience(**overrides):
    return _Row(
        **{
            "employer_name": "株式会社サンプル",
            "employer_name_english": None,
            "job_title": "エンジニア",
            "started_on": date(2021, 4, 1),
            "ended_on": None,
            "description": "ビルドを速くした",
            **overrides,
        }
    )


def _education(**overrides):
    return _Row(
        **{
            "institution": "サンプル大学",
            "institution_english": None,
            "qualification": "学士",
            "field_of_study": "情報工学",
            "started_on": date(2013, 4, 1),
            "ended_on": date(2017, 3, 31),
            **overrides,
        }
    )


def _certification(**overrides):
    return _Row(
        **{
            "name": "基本情報技術者",
            "name_english": None,
            "issuer": "情報処理推進機構",
            "issuer_english": None,
            "issued_on": date(2019, 10, 1),
            **overrides,
        }
    )


def _approved(entry_type, entry_id, field, text, language=Locale.en):
    """`language` is set explicitly, because the column's default is applied
    at insert and these rows are never flushed. A row read back from the
    database always carries one; a unit test's row only does if it says so,
    and a helper that left it `None` would make every lookup here miss for
    a reason that has nothing to do with what is being tested."""
    return EntryTranslation(
        profile_id=uuid.uuid4(),
        entry_type=entry_type,
        entry_id=entry_id,
        field=field,
        language=language,
        approved_text=text,
        approved_at=datetime.now(UTC),
        source_fingerprint="0" * 64,
    )


class TestOrder:
    def test_experience_runs_newest_first(self):
        old = _experience(started_on=date(2015, 4, 1), ended_on=date(2018, 3, 31))
        new = _experience(started_on=date(2021, 4, 1))

        content = build_content(_identity(), experiences=[old, new])

        assert [e.started_on for e in content.experiences] == [date(2021, 4, 1), date(2015, 4, 1)]

    def test_an_ongoing_role_is_not_buried_beneath_finished_ones(self):
        """Sorting by `ended_on` would put the user's current job last: it
        has no end date, which is the whole point of it."""
        ongoing = _experience(started_on=date(2019, 4, 1), ended_on=None)
        finished = _experience(started_on=date(2015, 4, 1), ended_on=date(2024, 3, 31))

        content = build_content(_identity(), experiences=[finished, ongoing])

        assert content.experiences[0].ended_on is None

    def test_an_entry_with_no_start_date_sorts_last(self):
        """Reading a missing date as "most recent" would put an entry at the
        top of the document on the strength of something the profile does
        not say."""
        undated = _experience(started_on=None, employer_name="Undated Co")
        dated = _experience(started_on=date(2015, 4, 1), employer_name="Dated Co")

        content = build_content(_identity(), experiences=[undated, dated])

        assert [e.employer for e in content.experiences] == ["Dated Co", "Undated Co"]

    def test_education_runs_newest_first_too(self):
        first = _education(started_on=date(2009, 4, 1))
        second = _education(started_on=date(2013, 4, 1))

        content = build_content(_identity(), education=[first, second])

        assert [e.started_on for e in content.education] == [date(2013, 4, 1), date(2009, 4, 1)]

    def test_certifications_run_newest_first(self):
        older = _certification(issued_on=date(2016, 4, 1))
        newer = _certification(issued_on=date(2021, 10, 1))

        content = build_content(_identity(), certifications=[older, newer])

        assert [c.issued_on for c in content.certifications] == [
            date(2021, 10, 1),
            date(2016, 4, 1),
        ]


class TestWhatTheProfileHoldsAndWhatItDoesNot:
    def test_an_employer_with_no_description_still_appears(self):
        """A role with nothing written about it is still a role. Dropping it
        would quietly shorten the document, which is the user's choice to
        make and never the projection's."""
        content = build_content(_identity(), experiences=[_experience(description="")])

        assert len(content.experiences) == 1
        assert content.experiences[0].description == ""

    def test_an_ongoing_role_keeps_its_open_end(self):
        content = build_content(_identity(), experiences=[_experience(ended_on=None)])

        assert content.experiences[0].ended_on is None

    def test_every_element_names_the_entry_behind_it(self):
        """FR-014. For any statement in the document, the entry it came from
        can be named — which is what makes a snapshot worth capturing."""
        identity = _identity()
        experience, education, skill, certification = (
            _experience(),
            _education(),
            _Row(name="Python", level=None),
            _certification(),
        )

        content = build_content(
            identity,
            experiences=[experience],
            education=[education],
            skills=[skill],
            certifications=[certification],
        )

        assert content.contact.source_entry_id == identity.id
        assert content.experiences[0].source_entry_id == experience.id
        assert content.education[0].source_entry_id == education.id
        assert content.skills[0].source_entry_id == skill.id
        assert content.certifications[0].source_entry_id == certification.id

    def test_skills_can_be_left_out_by_the_user(self):
        """Shortening is the user's choice through `include_skills`, never
        the renderer's (FR-007)."""
        skill = _Row(name="Python", level=None)

        assert build_content(_identity(), skills=[skill], include_skills=False).skills == ()
        assert len(build_content(_identity(), skills=[skill]).skills) == 1


class TestWhichEnglishIsUsed:
    def test_a_supplied_employer_name_wins(self):
        """The company's own English name, as the user stated it (FR-021)."""
        entry = _experience(employer_name_english="Sample Corporation")

        content = build_content(_identity(), experiences=[entry])

        assert content.experiences[0].employer == "Sample Corporation"

    def test_without_one_the_name_appears_as_recorded(self):
        """Never transliterated and never guessed, which is why this
        document still embeds a CJK font (R-007)."""
        content = build_content(_identity(), experiences=[_experience()])

        assert content.experiences[0].employer == "株式会社サンプル"

    def test_a_blank_supplied_name_is_not_a_name(self):
        content = build_content(_identity(), experiences=[_experience(employer_name_english="   ")])

        assert content.experiences[0].employer == "株式会社サンプル"

    def test_an_approved_translation_is_used_for_a_job_title(self):
        entry = _experience()
        content = build_content(
            _identity(),
            experiences=[entry],
            translations=[
                _approved(TranslatableEntry.work_experience, entry.id, "job_title", "Engineer")
            ],
        )

        assert content.experiences[0].job_title == "Engineer"

    def test_without_one_the_text_appears_as_recorded(self):
        """Not a failure and not a refusal: the entry appears in Japanese and
        readiness says so before the document is asked for (FR-017)."""
        content = build_content(_identity(), experiences=[_experience()])

        assert content.experiences[0].job_title == "エンジニア"

    def test_an_approval_for_a_different_field_is_not_borrowed(self):
        entry = _experience()
        content = build_content(
            _identity(),
            experiences=[entry],
            translations=[
                _approved(
                    TranslatableEntry.work_experience, entry.id, "description", "Made builds fast"
                )
            ],
        )

        assert content.experiences[0].job_title == "エンジニア", "the title is not the description"
        assert content.experiences[0].description == "Made builds fast"

    def test_an_approval_for_a_different_entry_is_not_borrowed(self):
        mine, theirs = _experience(), _experience()
        content = build_content(
            _identity(),
            experiences=[mine],
            translations=[
                _approved(TranslatableEntry.work_experience, theirs.id, "job_title", "Engineer")
            ],
        )

        assert content.experiences[0].job_title == "エンジニア"

    def test_an_approval_of_the_same_field_on_another_type_is_not_borrowed(self):
        """`entry_id` is not a foreign key, so the type is part of the key
        and this is what says so."""
        entry = _experience()
        content = build_content(
            _identity(),
            experiences=[entry],
            translations=[_approved(TranslatableEntry.skill, entry.id, "job_title", "Engineer")],
        )

        assert content.experiences[0].job_title == "エンジニア"

    def test_a_blank_approval_does_not_replace_the_source(self):
        """FR-025 refuses one at approval. Were one ever stored, printing it
        would take the entry out of the document with nothing to tell the
        user it had gone."""
        entry = _experience()
        content = build_content(
            _identity(),
            experiences=[entry],
            translations=[
                _approved(TranslatableEntry.work_experience, entry.id, "job_title", "   ")
            ],
        )

        assert content.experiences[0].job_title == "エンジニア"

    def test_another_language_is_not_used_for_an_english_resume(self):
        """`en` is the only value stored today and the column exists so a
        third language is a row rather than a migration. On the day that
        happens, a lookup keyed without the language would put someone's
        German into their English resume and say nothing about it."""
        entry = _experience()
        content = build_content(
            _identity(),
            experiences=[entry],
            translations=[
                _approved(
                    TranslatableEntry.work_experience,
                    entry.id,
                    "job_title",
                    "Ingenieur",
                    language=Locale.ja,
                )
            ],
        )

        assert content.experiences[0].job_title == "エンジニア"

    def test_a_stale_approval_is_still_the_user_s_wording(self):
        """FR-023: where the source was edited after approval, the approved
        English is kept, the divergence is reported, and generation is not
        blocked. Replacing it with the newer Japanese would be this module
        deciding something the requirement gives to the user — and the
        snapshot records what was actually used, so what was sent stays
        inspectable (R-010).

        The fingerprint here is of text the entry no longer holds, which is
        exactly what "stale" means.
        """
        entry = _experience(job_title="シニアエンジニア")
        content = build_content(
            _identity(),
            experiences=[entry],
            translations=[
                _approved(TranslatableEntry.work_experience, entry.id, "job_title", "Engineer")
            ],
        )

        assert content.experiences[0].job_title == "Engineer"

    def test_a_certification_uses_supplied_names_only(self):
        """It is in no translation at all: a name, an issuer and two dates
        means the first two are proper nouns and the last two are not words
        (R-002)."""
        entry = _certification(
            name_english="Fundamental Information Technology Engineer",
            issuer_english="Information-technology Promotion Agency",
        )

        content = build_content(_identity(), certifications=[entry])

        assert content.certifications[0].name == "Fundamental Information Technology Engineer"
        assert content.certifications[0].issuer == "Information-technology Promotion Agency"

    def test_a_certification_without_an_issuer_has_none(self):
        content = build_content(_identity(), certifications=[_certification(issuer=None)])

        assert content.certifications[0].issuer is None

    def test_an_english_issuer_survives_a_missing_japanese_one(self):
        """A profile may name the certificate and not who awarded it. A user
        who then supplies the English issuer has said something, and
        dropping it because the field it would fall back to is empty throws
        away the only answer they gave."""
        entry = _certification(
            issuer=None, issuer_english="Information-technology Promotion Agency"
        )

        content = build_content(_identity(), certifications=[entry])

        assert content.certifications[0].issuer == "Information-technology Promotion Agency"


class TestNoProviderIsReached:
    def test_building_content_opens_no_socket(self, monkeypatch):
        """R-005: generation reads approved English and renders it. A
        missing version is a readiness failure, never a translation
        performed on the spot — which is what keeps the same profile
        producing the same document twice."""
        import socket

        def refuse(*args, **kwargs):
            raise AssertionError("the projection reached for the network")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)

        content = build_content(_identity(), experiences=[_experience()])

        assert content.experiences[0].job_title == "エンジニア"


class TestWhatTheRendererCannotBeGiven:
    """FR-009 and FR-010, as a shape rather than a filter.

    The renderer is handed these dataclasses and nothing else. A layout
    change cannot leak a field its input type does not carry, and adding one
    would be a visible diff with the requirement written beside it.

    Feature 004 passed the same gate by never fetching `JapanProfile`. This
    goes one step further: never fetching it *and* having nowhere to put it.
    """

    DATACLASSES = (
        Contact,
        ExperienceEntry,
        EducationEntry,
        SkillEntry,
        CertificationEntry,
        ResumeContent,
    )

    #: Read off the table rather than listed, so a column added to
    #: `JapanProfile` tomorrow is forbidden tomorrow. A hardcoded list of
    #: three keeps passing on exactly the day it needs to fail.
    FORBIDDEN = {column.name for column in JapanProfile.__table__.columns} | {
        "date_of_birth",
        "address",
        "photo",
        "photograph",
        "full_name_japanese",
        "furigana",
    } - {"id", "profile_id", "created_at", "updated_at"}

    @pytest.mark.parametrize("cls", DATACLASSES, ids=lambda c: c.__name__)
    def test_it_has_no_field_the_document_must_never_show(self, cls):
        carried = {field.name for field in dataclasses.fields(cls)}
        assert not carried & self.FORBIDDEN, sorted(carried & self.FORBIDDEN)

    def test_the_forbidden_set_is_not_empty(self):
        """The test above passes trivially if this ever goes empty — for
        instance if `JapanProfile` were renamed and the import quietly
        resolved to something else."""
        assert "nationality" in self.FORBIDDEN
        assert "residence_status" in self.FORBIDDEN
        assert len(self.FORBIDDEN) > 5

    @pytest.mark.parametrize("cls", DATACLASSES, ids=lambda c: c.__name__)
    def test_it_is_frozen(self, cls):
        """A renderer that could assign to its input could also assign a
        field onto it. Frozen is what makes the absence hold at runtime and
        not only at the definition."""
        assert cls.__dataclass_params__.frozen

    def test_the_projection_never_asks_for_a_japan_profile(self):
        """The argument list is the other half: there is no parameter to
        pass one in through, disclosed or not."""
        import inspect

        parameters = set(inspect.signature(build_content).parameters)
        assert "japan" not in parameters and "japan_profile" not in parameters
