"""Facts about text that more than one feature needs to know.

Script detection lives here rather than beside the first feature that
wanted it. The 履歴書's readiness report asks whether an entry will appear
in English on a Japanese page; the translation routes ask whether there is
any Japanese to render into English. Those are the same question about the
characters, and two copies of the answer would drift the first time one of
them learned something — which has already happened once, when half-width
katakana turned out to matter (#107).
"""

import re

# Kana and kanji. An entry whose text has none of these reads as English.
#
# Half-width katakana is in here because imported data is full of it: it is
# what older Japanese systems emit, and feature 002 reads documents produced
# by exactly those systems. Without it a name written only that way is
# reported as having no Japanese version, while the same name carrying two
# kanji is not (#107).
#
# Written as escapes with the block each range covers: as literal characters
# the pattern is a row of glyphs nobody can check against the standard.
JAPANESE = re.compile(
    "["
    "぀-ヿ"  # hiragana and katakana
    "㐀-鿿"  # kanji, including extension A
    "豈-﫿"  # compatibility ideographs
    "ｦ-ﾝ"  # half-width katakana
    "]"
)


def has_japanese(value: str | None) -> bool:
    """Whether this text contains any Japanese script at all.

    One character is enough. A description written in English that names
    one Japanese company in kanji is still a description with Japanese in
    it, and a renderer asked to translate it has something to do.
    """
    return bool(value) and bool(JAPANESE.search(value))
