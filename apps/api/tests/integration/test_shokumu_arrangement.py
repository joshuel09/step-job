"""Quickstart Scenario 2 — the arrangement changes the order, nothing else.

FR-007 offers two arrangements; FR-008 says every one of them carries the same
set of entries. The failure this guards against is not a wrong order, which a
reader would notice. It is an entry quietly gained, lost, merged or shortened
on the way through a second code path — which a reader would not, because they
have no copy of the other document to compare against.

So the test is a comparison rather than a list of expectations: produce both,
and hold the two to carrying exactly the same lines.
"""

import io
import re

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"


def _generate(client, auth_headers, arrangement: str) -> bytes:
    response = client.post(PATH, headers=auth_headers, json={"arrangement": arrangement})
    assert response.status_code == 200, response.text
    return response.content


def _lines(pdf: bytes) -> list[str]:
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _squashed(pdf: bytes) -> str:
    return re.sub(r"[\s　]+", "", "".join(_lines(pdf)))


def _history(pdf: bytes) -> str:
    """Just the 職務経歴 section, where the arrangement actually applies.

    Matched on whole lines rather than on the squashed text: the document's
    own title is 職務経歴書, and 職務要約 names the most recent employer, so a
    search over the whole document finds the wrong occurrence of both.
    """
    lines = _lines(pdf)
    start = lines.index("職務経歴") + 1
    end = next(
        (i for i, line in enumerate(lines[start:], start) if line in _AFTER_HISTORY),
        len(lines),
    )
    return re.sub(r"[\s　]+", "", "".join(lines[start:end]))


_AFTER_HISTORY = {"その他の実績", "活かせる経験・知識・技術"}


def _line_with(pdf: bytes, needle: str) -> int:
    """Which line a value is on, matched on the line's squashed form.

    `Example Corp` is drawn with the space it was recorded with, so a search
    for the squashed spelling finds nothing in the lines as extracted.
    """
    for number, line in enumerate(_lines(pdf)):
        if needle in re.sub(r"[\s　]+", "", line):
            return number
    raise AssertionError(f"{needle!r} is not in the document")


@pytest.fixture
def both(client, auth_headers, shokumu_profile):
    return (
        _generate(client, auth_headers, "reverse_chronological"),
        _generate(client, auth_headers, "chronological"),
    )


class TestOnlyTheOrderDiffers:
    def test_the_two_carry_the_identical_set_of_lines(self, both):
        newest, oldest = both
        assert sorted(_lines(newest)) == sorted(_lines(oldest))

    def test_and_they_are_genuinely_in_a_different_order(self, both):
        """Otherwise the test above passes on an arrangement that does nothing."""
        newest, oldest = both
        assert _lines(newest) != _lines(oldest)

    def test_the_newest_employer_leads_one_and_closes_the_other(self, both):
        newest, oldest = (_history(pdf) for pdf in both)

        assert newest.index("ExampleCorp") < newest.index("株式会社サンプル")
        assert oldest.index("ExampleCorp") > oldest.index("株式会社サンプル")

    def test_no_entry_is_gained_or_lost(self, both):
        """Counted rather than searched for, so a duplicated line is caught too.

        The two must agree on how many times each value appears. Not on it
        appearing once: 職務要約 names the most recent employer and role, so
        those legitimately appear twice in both documents.
        """
        for recorded in (
            "株式会社サンプル",
            "ExampleCorp",
            "ビルド時間を半分にした",
            "社外勉強会の運営",
            "基本情報技術者",
        ):
            counts = {_squashed(pdf).count(recorded) for pdf in both}
            assert len(counts) == 1, f"{recorded} appears {counts} times across the two"
            assert counts != {0}, f"{recorded} is in neither document"

    def test_nothing_is_shortened_to_fit_the_other_order(self, both):
        for pdf in both:
            document = _squashed(pdf)
            assert "社内システムの開発と保守を担当。" in document
            assert "Platformworkonthebillingservice." in document

    def test_the_closing_section_stays_closing_in_both(self, both):
        """An unattached achievement follows the employers whichever way they
        run — it belongs to none of them, so it cannot lead (R-005)."""
        for pdf in both:
            closing = _line_with(pdf, "その他の実績")
            assert closing > _line_with(pdf, "ExampleCorp")
            assert closing > _line_with(pdf, "株式会社サンプル")


class TestWhatIsNotOffered:
    def test_an_unknown_arrangement_is_refused(self, client, auth_headers, shokumu_profile):
        """Grouping by project is not offered: the profile holds no project
        entity, and a career story has no client, period or role to build one
        from (R-004)."""
        response = client.post(PATH, headers=auth_headers, json={"arrangement": "by_project"})
        assert response.status_code == 422

    def test_the_refusal_names_the_field(self, client, auth_headers, shokumu_profile):
        response = client.post(PATH, headers=auth_headers, json={"arrangement": "by_project"})
        assert any("arrangement" in f["field"] for f in response.json()["failures"])

    def test_the_default_is_reverse_chronological(self, client, auth_headers, shokumu_profile):
        asked = _squashed(_generate(client, auth_headers, "reverse_chronological"))
        unasked = _squashed(client.post(PATH, headers=auth_headers, json={}).content)
        assert asked == unasked
