"""Quickstart Scenarios 1 and 10 — a profile becomes a career history.

Scenario 1: record two employers, one with an achievement, and generate. Every
employer appears with its period, title and description; the career stories
appear in the user's own words; the other sections have their lines.

Scenario 10: a profile with no name, and a profile with no work history, are
each refused with the missing thing named. Neither returns a document.

Every assertion reads text back out of the produced file. A page of hollow
boxes is the right size and passes any check on bytes, so asserting on the
file would prove nothing about what an employer sees.
"""

import io
import re
import uuid
from datetime import date

import pytest
from pypdf import PdfReader
from sqlalchemy import func, select

PATH = "/api/v1/profile/documents/shokumu-keirekisho"


def _generate(client, auth_headers, body: dict | None = None):
    response = client.post(PATH, headers=auth_headers, json=body or {})
    assert response.status_code == 200, response.text
    return response


def _squashed(pdf: bytes) -> str:
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    return re.sub(r"[\s　]+", "", text)


@pytest.fixture
def document(client, auth_headers, shokumu_profile) -> str:
    return _squashed(_generate(client, auth_headers).content)


class TestEveryEmployerAppears:
    def test_both_employers_are_named(self, document):
        assert "株式会社サンプル" in document
        assert "ExampleCorp" in document

    def test_each_carries_its_period(self, document):
        assert "2013年4月〜2021年3月" in document
        assert "2021年4月〜現在" in document, "an ongoing role ends at 現在, not a date"

    def test_each_carries_its_role_and_employment_type(self, document):
        assert "エンジニア" in document
        assert "SoftwareEngineer" in document
        assert "正社員" in document
        assert "契約社員" in document

    def test_each_carries_its_description(self, document):
        assert "社内システムの開発と保守を担当。" in document
        assert "Platformworkonthebillingservice." in document

    def test_the_newest_employer_comes_first_by_default(self, document):
        assert document.index("ExampleCorp") < document.index("株式会社サンプル")


class TestEveryAchievementAppears:
    def test_a_recorded_story_appears_in_the_user_s_own_words(self, document):
        assert "ビルド時間を半分にした" in document
        assert "ビルドに四十分かかっていた。" in document
        assert "分割して遅い工程をキャッシュした。" in document
        assert "二十分になった。" in document

    def test_it_sits_under_the_employer_it_belongs_to(self, document):
        """Between that employer's name and the next section's heading."""
        start = document.index("株式会社サンプル")
        assert document.index("ビルド時間を半分にした") > start

    def test_an_achievement_with_no_employer_still_appears(self, document):
        """FR-021: nothing recorded is dropped from the document."""
        assert "社外勉強会の運営" in document

    def test_the_closing_section_is_not_called_what_the_employer_sections_are(self, document):
        """A reader has to be able to tell that these belong to no employer.
        Two identical headings would say nothing."""
        assert "その他の実績" in document

    def test_it_is_not_filed_under_an_employer_it_was_never_recorded_against(
        self, client, auth_headers, session, shokumu_profile
    ):
        from app.career import models

        unattached = session.scalars(
            select(models.CareerStory).where(models.CareerStory.work_experience_id.is_(None))
        ).one()
        assert unattached.title == "社外勉強会の運営"

        document = _squashed(_generate(client, auth_headers).content)
        # It appears after both employer sections, in the closing one.
        assert document.index("社外勉強会の運営") > document.index("株式会社サンプル")
        assert document.index("社外勉強会の運営") > document.index("ExampleCorp")


class TestTheOtherSections:
    def test_the_summary_states_what_can_be_counted(self, document):
        assert "職務経験年数" in document
        assert "在籍企業数2社" in document
        assert "直近の職務" in document

    def test_skills_languages_and_certifications_are_drawn(self, document):
        assert "SQL" in document
        assert "上級" in document
        assert "日本語" in document
        assert "母語" in document
        assert "基本情報技術者" in document
        assert "情報処理推進機構" in document

    def test_自己PR_is_labelled_and_empty(self, document):
        """FR-020: the product does not write a claim about what kind of
        worker someone is. The heading says the blank is a decision."""
        assert "自己PR" in document
        assert document.rstrip().endswith("以上")

    def test_a_職務経歴書_is_not_a_履歴書(self, document):
        """It is a career history, so it carries no 学歴 and no personal
        details. The profile holds a date of birth; this document has no box
        for one, and printing it anyway would hand an employer something the
        user asked for in a different document (data-model)."""
        assert "学歴" not in document
        assert "1990" not in document
        assert "生年月日" not in document


class TestTheResponse:
    def test_a_snapshot_id_comes_back(self, client, auth_headers, shokumu_profile):
        response = _generate(client, auth_headers)
        uuid.UUID(response.headers["X-Snapshot-Id"])

    def test_the_page_count_comes_back(self, client, auth_headers, shokumu_profile):
        assert int(_generate(client, auth_headers).headers["X-Document-Pages"]) >= 1

    def test_the_snapshot_names_every_entry_the_document_drew_on(
        self, client, auth_headers, session, shokumu_profile
    ):
        from app.career import models

        response = _generate(client, auth_headers)
        snapshot = session.get(models.EntrySnapshot, uuid.UUID(response.headers["X-Snapshot-Id"]))

        captured = set(snapshot.captured_entry_ids)
        for model in (
            models.Identity,
            models.WorkExperience,
            models.CareerStory,
            models.Skill,
            models.Language,
            models.Certification,
        ):
            for entry in session.scalars(
                select(model).where(model.profile_id == shokumu_profile.id)
            ):
                assert entry.id in captured, f"{model.__name__} {entry.id} is not in the snapshot"

    def test_the_document_itself_is_not_retained(self, client, auth_headers, shokumu_profile):
        """FR-005. `test_nothing_in_the_schema_can_hold_a_generated_document`
        in feature 003 walks every table in `Base.metadata` and so already
        covers this feature; stated here so the guarantee is deliberate rather
        than accidental."""
        from app.career import models

        _generate(client, auth_headers)
        assert "pdf" not in {c.name for c in models.EntrySnapshot.__table__.columns}


class TestRefusedRatherThanEmpty:
    """Scenario 10 — FR-006."""

    def test_a_profile_with_no_name_is_refused_naming_identity(
        self, client, auth_headers, session, user_id
    ):
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
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

        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 422, response.text
        assert [f["field"] for f in response.json()["failures"]] == ["identity"]

    def test_a_profile_with_no_work_history_is_refused_saying_so(
        self, client, auth_headers, session, user_id
    ):
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.flush()

        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 422, response.text
        assert [f["field"] for f in response.json()["failures"]] == ["experiences"]

    def test_a_profile_missing_both_names_both(self, client, auth_headers, session, user_id):
        from app.career import service

        service.get_or_create_profile(session, user_id)

        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 422
        assert [f["field"] for f in response.json()["failures"]] == ["identity", "experiences"]

    def test_a_refusal_returns_no_document(self, client, auth_headers, session, user_id):
        from app.career import service

        service.get_or_create_profile(session, user_id)

        response = client.post(PATH, headers=auth_headers, json={})
        assert response.headers["content-type"].startswith("application/json")
        assert b"%PDF" not in response.content

    def test_a_refusal_records_no_snapshot(self, client, auth_headers, session, user_id):
        """A render that never happened must leave no record of a document
        nobody received (R-006)."""
        from app.career import models, service

        service.get_or_create_profile(session, user_id)

        def count() -> int:
            return session.scalar(select(func.count()).select_from(models.EntrySnapshot))

        before = count()
        assert client.post(PATH, headers=auth_headers, json={}).status_code == 422
        assert count() == before

    def test_a_caller_with_no_profile_at_all_gets_a_404(self, client, auth_headers):
        assert client.post(PATH, headers=auth_headers, json={}).status_code == 404


# Every word the document is allowed to supply itself, written out here rather
# than imported from the renderer. The module's own constants cannot be the
# oracle for a test about what the module may say: a sentence added to 自己PR
# would be subtracted as vocabulary and this would pass on the invention it
# exists to forbid. Changing the document's wording is a deliberate act, and
# it fails here until it is made deliberately.
VOCABULARY = (
    # Headings, in the order they are drawn.
    "職務経歴書",
    "氏名",
    "作成日",
    "職務要約",
    "職務経歴",
    "活かせる経験・知識・技術",
    "語学",
    "免許・資格",
    "自己PR",
    "その他の実績",
    "実績",
    "以上",
    # Labels inside a section.
    "期間",
    "職種",
    "雇用形態",
    "課題",
    "取組",
    "成果",
    # The summary's own words.
    "職務経験年数",
    "在籍企業数",
    "直近の職務",
    # Values the profile stores as an enumeration, which are the product's
    # vocabulary rather than the user's words.
    "正社員",
    "契約社員",
    "上級",
    "母語",
    # Punctuation and the open end of an ongoing role.
    "現在",
    "〜",
    "（",
    "）",
    "・",
    "年",
    "月",
    "日",
    "社",
)

# Everything the fixture records, which is what the document may repeat.
RECORDED = (
    "山田太郎",
    "株式会社サンプル",
    "エンジニア",
    "社内システムの開発と保守を担当。",
    "Example Corp",
    "Software Engineer",
    "Platform work on the billing service.",
    "ビルド時間を半分にした",
    "ビルドに四十分かかっていた。",
    "分割して遅い工程をキャッシュした。",
    "二十分になった。",
    "社外勉強会の運営",
    "参加者が集まらなかった。",
    "告知の方法を変えた。",
    "毎回三十名が参加した。",
    "SQL",
    "日本語",
    "基本情報技術者",
    "情報処理推進機構",
)


class TestNothingIsInvented:
    """FR-012, FR-013, FR-020 — the document says nothing the profile lacks.

    The strongest test in this file, because it is the only one that fails for
    a sentence nobody thought to forbid. Every character on the page must be
    the user's, a date, a number, or a word from the list above.
    """

    def test_every_word_on_the_page_is_accounted_for(self, document):
        left = document
        for value in sorted(RECORDED, key=len, reverse=True):
            left = left.replace(re.sub(r"[\s　]+", "", value), "")
        # Dates and counts.
        left = re.sub(r"[0-9]+", "", left)
        for word in sorted(VOCABULARY, key=len, reverse=True):
            left = left.replace(word, "")

        assert left == "", f"the document says something the profile does not hold: {left!r}"

    def test_an_employer_with_no_description_gets_no_narrative(
        self, client, auth_headers, session, shokumu_profile
    ):
        """FR-013: a section with nothing recorded stays empty rather than
        being filled with something plausible."""
        from app.career import models

        for entry in session.scalars(select(models.WorkExperience)):
            entry.description = ""
        session.flush()

        left = _squashed(_generate(client, auth_headers).content)
        for value in sorted(RECORDED, key=len, reverse=True):
            left = left.replace(re.sub(r"[\s　]+", "", value), "")
        left = re.sub(r"[0-9]+", "", left)
        for word in sorted(VOCABULARY, key=len, reverse=True):
            left = left.replace(word, "")

        assert left == "", f"an empty description was filled in: {left!r}"

    def test_自己PR_has_nothing_under_it(self, document):
        """The product does not write a claim about what kind of worker
        someone is (FR-020). Between its heading and 以上 there is nothing."""
        tail = document[document.index("自己PR") + len("自己PR") :]
        assert tail.strip() == "以上", f"自己PR was written for the user: {tail!r}"
