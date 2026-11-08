"""The profile projected into what an English resume may show.

The order and the fallbacks are ordinary tests. `TestWhatTheRendererCannotBeGiven`
is not: it is the mechanism FR-009 and FR-010 rest on, written as a test
because the mechanism is an absence and an absence is the easiest thing in a
codebase to reintroduce by accident.

The forbidden names are read off `JapanProfile` rather than listed here. A
list of three would keep passing on the day someone adds a fourth column to
that table, which is the day it would need to fail.
"""

import ast
import dataclasses
import json
import pathlib
import textwrap
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


class TestTheTableIsNeverNamed:
    """The exclusion is by never fetching, not by filtering after (FR-010).

    `TestWhatTheRendererCannotBeGiven` covers the shape the renderer is
    handed. This covers everything upstream of it: a `select(JapanProfile)`
    in `service.py` would leave the row loaded in the session, where the
    next log line, debug repr or convenience helper can reach it — and the
    dataclass guard would still pass, because the leak would never have to
    go through the dataclasses at all.

    Static, deliberately. The integration suite captures the SQL a real
    generation issues, which is the stronger check and the slower one; this
    one is what fails in the editor, naming the file.
    """

    RESUME = pathlib.Path(__file__).resolve().parents[2] / "app" / "resume"

    @staticmethod
    def _names(path: pathlib.Path) -> set[str]:
        """Every mention of the model or its table in one module.

        Four ways to name it, because the narrow reading of any one of them
        is a way through. The model by name or by attribute; the import
        that brings it in, which is a mention before it is ever used; and
        the table in a string — matched anywhere in one rather than as the
        whole of it, since `text("select ... from japan_profile ...")` is
        the form this would actually take.

        Prose is not a mention. The docstrings in this package explain at
        length why `JapanProfile` is absent, and a guard that forbade
        saying so would be a guard against the explanation — so the
        docstring of a module, class or function is skipped, and
        `test_prose_about_it_is_not_a_mention` is what keeps that from
        becoming the hole.
        """
        tree = ast.parse(path.read_text())
        prose = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }

        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "JapanProfile":
                found.add(node.id)
            elif isinstance(node, ast.Attribute) and node.attr == "JapanProfile":
                found.add(node.attr)
            elif isinstance(node, ast.alias) and node.name.split(".")[-1] == "JapanProfile":
                found.add("JapanProfile")
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in prose
                and "japan_profile" in node.value.lower()
            ):
                found.add("japan_profile")
        return found

    def _written(self, tmp_path: pathlib.Path, source: str) -> set[str]:
        """What the walk finds in a module written here rather than on disk.

        The three tests below are about the reading, not about the package,
        and a module under `app/resume/` that existed to be caught would be
        a module shipped to fail a test.
        """
        module = tmp_path / "written.py"
        module.write_text(textwrap.dedent(source))
        return self._names(module)

    def test_nothing_under_app_resume_names_it(self):
        offenders = {
            path.relative_to(self.RESUME.parent).as_posix(): sorted(named)
            for path in sorted(self.RESUME.rglob("*.py"))
            if (named := self._names(path))
        }
        assert not offenders, offenders

    def test_there_were_modules_to_read(self):
        """An empty directory, a renamed package or a changed layout would
        satisfy the test above without reading a line."""
        modules = {path.name for path in self.RESUME.rglob("*.py")}
        assert {"sections.py", "service.py", "render.py", "readiness.py"} <= modules

    def test_the_walk_finds_the_name_where_it_belongs(self):
        """The positive control. `snapshots.py` names the model on purpose —
        a 履歴書 captures disclosed fields from it — so the walk that reports
        nothing under `app/resume/` must report something here."""
        snapshots = self.RESUME.parent / "career" / "snapshots.py"
        assert self._names(snapshots) == {"JapanProfile"}

    def test_an_import_is_a_mention_before_it_is_used(self, tmp_path):
        """An import on its own, with no use of the name anywhere. It would
        be flagged as unused today — but the day someone adds the use and
        the walk only looks at uses, the import was never the warning."""
        found = self._written(
            tmp_path,
            """
            from app.career.models import JapanProfile
            """,
        )

        assert found == {"JapanProfile"}

    def test_the_table_named_inside_a_string_is_a_mention(self, tmp_path):
        """The form this would really take. A model class is easy to see in
        review; a table name inside a SQL string is the way a value gets
        fetched without anything in the module looking like a fetch."""
        found = self._written(
            tmp_path,
            """
            from sqlalchemy import text

            def leak(session):
                return session.execute(text("SELECT nationality FROM japan_profile"))
            """,
        )

        assert found == {"japan_profile"}

    def test_prose_about_it_is_not_a_mention(self, tmp_path):
        """And this is what the skipping is for. Every module in the
        package explains the absence, and naming the table while doing so
        has to stay allowed or the explanation goes out with the leak."""
        found = self._written(
            tmp_path,
            """
            \"\"\"Nothing here reads japan_profile, and that is the point.\"\"\"

            def build():
                \"\"\"Never touches japan_profile.\"\"\"
                return None
            """,
        )

        assert found == set()


class TestWhatIsReadFromTheIdentity:
    """Three fields out of a row that holds seven (FR-009).

    The row is handed to the projection whole — there is no narrowed query
    upstream — so what is read from it is decided here, and that is the
    thing worth a test. Asserted against the projection serialised, not
    against the dataclass fields: a value smuggled into a name or a phone
    number would pass a check on field names.
    """

    IDENTITY = {
        "full_name_latin": "Taro Yamada",
        "email": "taro@example.com",
        "phone": "090-0000-0000",
        "full_name_japanese": "山田太郎",
        "furigana": "ヤマダタロウ",
        "date_of_birth": date(1990, 5, 15),
        "address": "東京都千代田区1-1-1",
    }

    @pytest.fixture
    def written(self):
        content = build_content(
            _identity(**self.IDENTITY),
            experiences=[_experience()],
        )
        return json.dumps(dataclasses.asdict(content), ensure_ascii=False, default=str)

    def test_the_three_it_reads_are_there(self, written):
        """The positive control: a projection that dropped the contact
        details entirely would satisfy every absence below."""
        for value in ("Taro Yamada", "taro@example.com", "090-0000-0000"):
            assert value in written

    @pytest.mark.parametrize(
        "field", ["full_name_japanese", "furigana", "date_of_birth", "address"]
    )
    def test_the_four_it_does_not_read_are_not(self, written, field):
        assert str(self.IDENTITY[field]) not in written

    def test_the_identity_row_offered_more_than_was_taken(self):
        """If `Identity` ever stopped carrying these, the test above would
        go on passing while guarding nothing."""
        from app.career.models import Identity

        columns = {column.name for column in Identity.__table__.columns}
        assert {"date_of_birth", "address", "full_name_japanese", "furigana"} <= columns
