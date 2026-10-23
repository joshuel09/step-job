"""Which scripts count as Japanese in the readiness report (#107).

The report decides whether an entry will read as English from the text
itself, not from its recorded source language — that field defaults to
English, so trusting it would tell a user their own 大学 has no Japanese
version.

So the whole decision rests on one pattern, and a range that is short at
either end is invisible until someone's name is wrongly reported. These pin
each block by its first and last character, which is the only way an
off-by-one in a range shows up: a realistic label has enough characters that
losing one of them changes nothing.
"""

import pytest
from app.rirekisho.readiness import _JAPANESE

# The first and last character of each block the pattern claims to cover.
BLOCKS = {
    "hiragana and katakana": ("぀", "ヿ"),
    "kanji, including extension A": ("㐀", "鿿"),
    "compatibility ideographs": ("豈", "﫿"),
    "half-width katakana": ("ｦ", "ﾝ"),
}


@pytest.mark.parametrize("block", BLOCKS)
def test_each_block_counts_at_both_ends(block):
    first, last = BLOCKS[block]
    assert _JAPANESE.search(first), f"{block} is short at the start"
    assert _JAPANESE.search(last), f"{block} is short at the end"


@pytest.mark.parametrize(
    "label",
    [
        "さくら",  # hiragana
        "サンプル",  # full-width katakana, no kanji to fall back on
        "株式会社",  # kanji
        "ｻﾝﾌﾟﾙｼｮｳｼﾞ",  # half-width katakana, which imported data is full of
        "ﾔﾏﾀﾞ",
        "ｻﾝﾌﾟﾙ商事",  # mixed: used to pass only because of the two kanji
    ],
)
def test_japanese_text_is_recognised(label):
    assert _JAPANESE.search(label)


@pytest.mark.parametrize(
    "label",
    [
        "Example Corp",
        "AWS Solutions Architect",
        "2020",
        "A-B-C",
        "",
        "   ",
    ],
)
def test_text_with_no_japanese_in_it_is_not(label):
    """The distinguishing half. A pattern wide enough to match anything would
    pass every test above and report nothing, ever."""
    assert not _JAPANESE.search(label)
