# Fonts

`ipaexg.ttf` — IPAex Gothic, version 004.01, from the Information-technology
Promotion Agency, Japan.

Shipped with the application rather than fetched at build time or taken from the
host. A missing Japanese font does not fail loudly: the document is produced at
the right size with every character rendered as a hollow box, and a developer
whose machine has Japanese system fonts may never reproduce it.

## Why a TrueType font rather than the CID fonts reportlab provides

Measured, not assumed:

| | PDF size, one glyph | Embeds glyph data |
|---|---|---|
| IPAex Gothic (TrueType) | 15.7 KB | **yes** |
| HeiseiKakuGo-W5 (CID) | 2.3 KB | no |

Both render and both extract back to text. The difference is that the CID font
is a reference the reader must resolve, and a 履歴書 is printed and handed to an
employer. A document that renders on the applicant's machine and not on the
reviewer's is worse than a larger file.

The font is subsetted per document, so the six megabytes here cost about fifteen
kilobytes in a generated 履歴書.

## Licence

IPA Font License Agreement v1.0, in `LICENSE.txt`. It permits redistribution,
including bundled with software, provided the licence travels with the font and
the font is not renamed. Both conditions are met by shipping it here unmodified.
