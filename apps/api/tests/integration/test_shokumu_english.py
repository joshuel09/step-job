"""Quickstart Scenario 11 — English entries stay English (FR-015).

Translating a job title is putting words in someone's mouth about their own
career. "Software Engineer" is not ソフトウェアエンジニア unless the user
wrote that: titles carry grade and scope that do not survive the trip, and
the person who signs the document is the one who has to defend the version
an employer reads.

A blocklist of likely translations only catches the ones someone thought of.
So this subtracts instead: take away the user's own values, the document's
fixed vocabulary and the dates, and assert no Japanese remains. The last test
plants a translation to prove the subtraction can still see one.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"

# Anything written in kana or kanji. Half-width katakana included, because
# imported data is full of it (#107).
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿豈-﫿ｦ-ﾝ]")

# Every word the document supplies itself, written out here rather than
# imported from the renderer: the module's own constants cannot be the oracle
# for a test about what the module may say.
VOCABULARY = (
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
    "期間",
    "職種",
    "雇用形態",
    "課題",
    "取組",
    "成果",
    "職務経験年数",
    "在籍企業数",
    "直近の職務",
    "正社員",
    "契約社員",
    "アルバイト・パート",
    "インターン",
    "業務委託",
    "初級",
    "中級",
    "上級",
    "エキスパート",
    "母語",
    "ビジネスレベル",
    "日常会話レベル",
    "基礎レベル",
    "現在",
    "年",
    "月",
    "日",
    "社",
    "令和",
    "平成",
    "昭和",
    # Punctuation the document supplies: the bullet before a list item, the
    # brackets round a qualifier, the tilde between two dates. The bullet is
    # U+30FB, which sits inside the katakana block, so it reads as Japanese
    # to the pattern above unless it is accounted for here.
    "・",
    "（",
    "）",
    "〜",
)


@pytest.fixture
def english_profile(session, user_id):
    """A career recorded entirely in English, as someone arriving from
    outside Japan would have it."""
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(models.Identity(profile_id=profile.id, full_name_latin="Maria Santos"))
    experience = models.WorkExperience(
        profile_id=profile.id,
        employer_name="Example Corp",
        employer_name_normalised="example",
        job_title="Senior Software Engineer",
        employment_type=models.EmploymentType.permanent,
        started_on=date(2018, 4, 1),
        ended_on=date(2024, 3, 31),
        description="Built and ran the billing service.",
        source_language=models.Locale.en,
    )
    session.add(experience)
    session.flush()
    session.add_all(
        [
            models.CareerStory(
                profile_id=profile.id,
                work_experience_id=experience.id,
                title="Cut the build in half",
                challenge="The build took forty minutes.",
                action="Split it and cached the slow step.",
                result="Twenty minutes.",
                source_language=models.Locale.en,
            ),
            models.Skill(profile_id=profile.id, name="PostgreSQL", level=models.SkillLevel.expert),
            models.Certification(
                profile_id=profile.id, name="AWS Solutions Architect", issuer="Amazon"
            ),
        ]
    )
    session.flush()
    return profile


RECORDED = (
    "Maria Santos",
    "Example Corp",
    "Senior Software Engineer",
    "Built and ran the billing service.",
    "Cut the build in half",
    "The build took forty minutes.",
    "Split it and cached the slow step.",
    "Twenty minutes.",
    "PostgreSQL",
    "AWS Solutions Architect",
    "Amazon",
)


def _document(client, auth_headers, **body) -> str:
    response = client.post(PATH, headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(response.content)).pages)
    return re.sub(r"[\s　]+", "", text)


def _left_after_subtracting(document: str) -> str:
    left = document
    for value in sorted(RECORDED, key=len, reverse=True):
        left = left.replace(re.sub(r"[\s　]+", "", value), "")
    left = re.sub(r"[0-9]+", "", left)
    for word in sorted(VOCABULARY, key=len, reverse=True):
        left = left.replace(word, "")
    return left


class TestEnglishArrivesAsWritten:
    def test_every_recorded_value_appears_exactly_as_recorded(
        self, client, auth_headers, english_profile
    ):
        document = _document(client, auth_headers)
        for value in RECORDED:
            assert re.sub(r"[\s　]+", "", value) in document, f"{value} was not written as recorded"

    def test_the_job_title_is_not_translated(self, client, auth_headers, english_profile):
        """The clearest case: a title carries grade and scope that do not
        survive being rendered into another language."""
        document = _document(client, auth_headers)
        assert "SeniorSoftwareEngineer" in document
        for rendering in ("ソフトウェアエンジニア", "上級エンジニア", "技術者"):
            assert rendering not in document


class TestNothingJapaneseThatWasNotWritten:
    def test_what_remains_after_subtraction_has_no_japanese_in_it(
        self, client, auth_headers, english_profile
    ):
        left = _left_after_subtracting(_document(client, auth_headers))
        found = JAPANESE.findall(left)
        assert found == [], f"japanese the user never wrote: {left!r}"

    def test_the_wareki_document_is_no_different(self, client, auth_headers, english_profile):
        left = _left_after_subtracting(_document(client, auth_headers, date_convention="wareki"))
        assert JAPANESE.findall(left) == [], f"japanese the user never wrote: {left!r}"

    def test_the_subtraction_can_still_see_a_translation(
        self, client, auth_headers, session, english_profile
    ):
        """The guard. Plant a translated title the user never wrote and the
        subtraction must find it, or the two tests above prove nothing."""
        from app.career import models
        from sqlalchemy import select

        role = session.scalars(
            select(models.WorkExperience).where(
                models.WorkExperience.profile_id == english_profile.id
            )
        ).one()
        planted = "上級ソフトウェア技術者"
        role.job_title = f"Senior Software Engineer（{planted}）"
        session.flush()

        left = _left_after_subtracting(_document(client, auth_headers))
        assert planted.replace("上級", "") in left or planted in left, (
            "the subtraction did not notice a planted translation"
        )
