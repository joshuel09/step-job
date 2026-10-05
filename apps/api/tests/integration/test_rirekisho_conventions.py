"""Quickstart Scenario 2 — the date convention the user chose, and only that one.

FR-019: one convention throughout a document. A 和暦 document with a single
Western year in it is a failure even if every date is correct, so these tests
look at the whole document rather than one date in the table.

The era conversion is round-trip tested on its own in the imports module; a
failure here is a rendering problem, not a conversion one.
"""

import io
import re

import pytest
from app.imports.dates import ERA_STARTS
from pypdf import PdfReader

ERA = re.compile("|".join(name for name, _ in ERA_STARTS))

# A calendar year written out in full. The address in the fixture has digits
# (1-2-3) but never four in a row, so anything this finds is a Western date.
WESTERN_YEAR = re.compile(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)")


def _text(content: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)


def _generate(client, auth_headers, body: dict) -> str:
    response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    return _text(response.content)


@pytest.fixture
def seireki(client, auth_headers, rirekisho_profile):
    return _generate(client, auth_headers, {"date_convention": "seireki"})


@pytest.fixture
def wareki(client, auth_headers, rirekisho_profile):
    return _generate(client, auth_headers, {"date_convention": "wareki"})


def test_seireki_writes_western_years(seireki):
    assert "2013年4月" in seireki
    assert "2021年4月" in seireki


def test_seireki_has_no_era_anywhere(seireki):
    assert ERA.findall(seireki) == []


def test_wareki_writes_era_years(wareki):
    """2013 and 2021 fall in different eras, so both names must appear."""
    assert "平成25年4月" in wareki
    assert "令和3年4月" in wareki


def test_wareki_has_no_western_year_anywhere(wareki):
    """FR-019: not in the table, and not in the identity block either."""
    assert WESTERN_YEAR.findall(wareki) == []


def test_the_date_of_birth_follows_the_convention(seireki, wareki):
    """The one date outside the table, and the easiest one to leave behind."""
    assert "1990年5月15日" in seireki
    assert "平成2年5月15日" in wareki


def test_the_convention_changes_only_the_dates(seireki, wareki):
    """Presentation differs; content does not."""
    for text in (seireki, wareki):
        assert "山田太郎" in text
        assert "サンプル大学" in text
        assert "株式会社サンプル" in text
        assert "現在に至る" in text
        assert "以上" in text


def test_no_convention_chosen_means_seireki(client, auth_headers, rirekisho_profile):
    """The contract's default, applied to the whole document."""
    text = _generate(client, auth_headers, {})
    assert "2013年4月" in text
    assert ERA.findall(text) == []
