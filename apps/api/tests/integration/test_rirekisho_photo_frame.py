"""#106 — the identity block keeps clear of the photograph frame.

An empty frame is drawn at the top right of page 1, where convention puts
it and where the user is expected to paste a photograph. Nothing used to
keep the identity lines out of it: a long 現住所 stopped at the right margin
like everything else and ran straight under the frame.

That loses nothing from the file — text extraction still finds the address —
and loses it from the printed page, which is the copy an employer reads.

So these check the geometry rather than the text: every string drawn on page
1 must lie outside the frame's rectangle, and the address must still be
there, whole, on the lines beside it.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

PATH = "/api/v1/profile/documents/rirekisho"

# Longer than the space beside the frame, so it has to wrap rather than run on.
LONG_ADDRESS = (
    "東京都千代田区丸の内一丁目九番二号グラントウキョウサウスタワー四十一階サンプル株式会社気付"
)
LONG_FURIGANA = "とうきょうとちよだくまるのうちいっちょうめきゅうばんにごうさんぷるかぶしきがいしゃ"
LONG_EMAIL = "yamada.taro.department.of.engineering@a-very-long-example-domain.co.jp"

# Sits well below the frame, and is long enough that a line of full width
# reaches past where the frame would have cut it short. Without a row like
# this, nothing below the frame is long enough to notice over-narrowing.
LONG_EMPLOYER = (
    "国立研究開発法人新エネルギー・産業技術総合開発機構ロボット・ＡＩ部先端技術研究センター"
)


@pytest.fixture
def photo_profile(session, user_id):
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Taro Yamada",
            full_name_japanese="山田太郎",
            furigana=LONG_FURIGANA,
            address=LONG_ADDRESS,
            email=LONG_EMAIL,
            phone="090-1234-5678",
            date_of_birth=date(1990, 4, 1),
        )
    )
    session.add(
        models.WorkExperience(
            profile_id=profile.id,
            employer_name=LONG_EMPLOYER,
            employer_name_normalised="long",
            job_title="エンジニア",
            started_on=date(2015, 4, 1),
            ended_on=date(2020, 3, 31),
        )
    )
    session.flush()
    return profile


def _generate(client, auth_headers, paper: str) -> bytes:
    response = client.post(PATH, headers=auth_headers, json={"paper_size": paper})
    assert response.status_code == 200, response.text
    return response.content


def _under_the_frame(pdf: bytes) -> list[str]:
    """Every string on page 1 that overlaps the photograph frame.

    The frame's own label sits below it and is expected to be clear; anything
    that is not clear would be hidden by a pasted photograph.
    """
    from app.rirekisho.render import FONT_NAME, MARGIN, PHOTO_HEIGHT, PHOTO_WIDTH

    page = PdfReader(io.BytesIO(pdf)).pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    left = width - MARGIN - PHOTO_WIDTH
    right = width - MARGIN
    bottom = height - MARGIN - PHOTO_HEIGHT
    top = height - MARGIN

    found: list[str] = []

    def visit(text, cm, tm, font, size):
        text = text.rstrip("\n")
        if not text.strip():
            return
        x, y = tm[4], tm[5]
        # A tenth of a point of contact is contact: a frame drawn over the
        # last character still hides it.
        if x + stringWidth(text, FONT_NAME, size) > left and x < right:
            if y + size > bottom and y < top:
                found.append(text)

    page.extract_text(visitor_text=visit)
    return found


def _squashed(pdf: bytes) -> str:
    text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    return re.sub(r"[\s　]+", "", text)


PAPERS = pytest.mark.parametrize("paper", ["a4", "b5"])


@PAPERS
class TestTheFrameCoversNothing:
    def test_no_line_runs_under_the_frame(self, client, auth_headers, photo_profile, paper):
        assert _under_the_frame(_generate(client, auth_headers, paper)) == []

    def test_the_address_is_still_there_whole(self, client, auth_headers, photo_profile, paper):
        """Kept clear by wrapping it, never by cutting it short (FR-018a)."""
        assert LONG_ADDRESS in _squashed(_generate(client, auth_headers, paper))

    def test_the_other_long_identity_lines_survive_too(
        self, client, auth_headers, photo_profile, paper
    ):
        text = _squashed(_generate(client, auth_headers, paper))
        assert LONG_FURIGANA in text
        assert LONG_EMAIL in text

    def test_the_frame_is_drawn_at_all(self, client, auth_headers, photo_profile, paper):
        """Otherwise the first test passes by having nothing to avoid."""
        assert "写真貼付欄" in _squashed(_generate(client, auth_headers, paper))


@PAPERS
def test_only_the_lines_beside_the_frame_are_narrowed(client, auth_headers, photo_profile, paper):
    """The rest of the document keeps its full width.

    Keeping clear of the frame is cheap to overdo: narrowing every line would
    pass the test above and quietly cost every later section a hundred points.
    The long employer below the frame is what makes that visible.
    """
    from app.rirekisho.render import FONT_NAME, MARGIN, PHOTO_GAP, PHOTO_WIDTH

    page = PdfReader(io.BytesIO(_generate(client, auth_headers, paper))).pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    narrowed = width - MARGIN - PHOTO_WIDTH - PHOTO_GAP
    below = height - MARGIN - 120

    reach: list[float] = []

    def visit(text, cm, tm, font, size):
        text = text.rstrip("\n")
        # Only lines of the document body. The frame's own label is below the
        # frame and starts at the frame's own x, so it reaches past the
        # narrowed edge however the body is wrapped — counting it would make
        # this assertion true no matter what.
        if text.strip() and tm[5] < below and tm[4] <= MARGIN + 1:
            reach.append(tm[4] + stringWidth(text, FONT_NAME, size))

    page.extract_text(visitor_text=visit)
    assert reach, "nothing was drawn below the frame, so this proves nothing"
    assert max(reach) > narrowed, "the whole document was narrowed, not just the identity block"


@pytest.fixture
def two_page_profile(session, user_id):
    """Long enough to need a second page, where there is no frame to avoid."""
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Taro Yamada",
            full_name_japanese="山田太郎",
        )
    )
    for i in range(40):
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name=f"{LONG_EMPLOYER}{i:02d}",
                employer_name_normalised=f"e{i}",
                job_title="エンジニア",
                started_on=date(1985 + i // 2, 1 + (i % 2) * 6, 1),
                ended_on=date(1985 + i // 2, 5 + (i % 2) * 6, 30),
            )
        )
    session.flush()
    return profile


@PAPERS
def test_later_pages_keep_their_full_width(client, auth_headers, two_page_profile, paper):
    """The frame is on page 1. Page 2 has nothing to avoid.

    The reservation is cleared at every page break; without that, every page
    after the first would lose a hundred points of width to a frame that is
    not there.
    """
    from app.rirekisho.render import (
        FONT_NAME,
        MARGIN,
        PHOTO_GAP,
        PHOTO_HEIGHT,
        PHOTO_WIDTH,
    )

    pages = PdfReader(io.BytesIO(_generate(client, auth_headers, paper))).pages
    assert len(pages) > 1, "this profile was meant to run past one page"

    width = float(pages[1].mediabox.width)
    narrowed = width - MARGIN - PHOTO_WIDTH - PHOTO_GAP
    reach: list[float] = []

    # Only the band a frame would occupy if there were one. Lower down the
    # page every line has its full width whether the reservation was lifted
    # or not, so looking at the whole page proves nothing.
    height = float(pages[1].mediabox.height)
    band = height - MARGIN - PHOTO_HEIGHT

    def visit(text, cm, tm, font, size):
        text = text.rstrip("\n")
        # Dated rows only. Every employer in this profile is long enough to
        # fill the line, so each of these reaches as far as it is allowed to;
        # the section heading beside them does not and would hide the fault.
        if "年" in text and tm[4] <= MARGIN + 1 and tm[5] > band:
            reach.append(tm[4] + stringWidth(text, FONT_NAME, size))

    pages[1].extract_text(visitor_text=visit)
    # The first row of a page was wrapped before the break, with the width it
    # had on the page before, so it is full width either way. The rows after
    # it are the ones that show whether the reservation was lifted.
    assert len(reach) > 1, "page 2's top band needs more than one dated row to prove anything"
    assert min(reach[1:]) > narrowed, "page 2 was narrowed for a frame it does not have"
