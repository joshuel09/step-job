"""What a 履歴書 would lack, said before it is printed rather than after.

A pure function from what the profile holds to a report, in three parts that
need three different responses from the user:

- **missing_required**: without these there is no document. Generation refuses,
  and it refuses using the same rule, so the report and the refusal cannot
  disagree about whether a document can be made (FR-015).
- **missing_optional**: these will simply be blank. The document is still
  produced; the user learns now that a box will be empty (FR-022c).
- **entries_without_japanese**: these will appear in English, as written. The
  user may add a Japanese version to their profile; nothing here writes one
  (research.md R-001).

Like the row projection, it knows nothing about PDFs and touches no database,
so every case can be tested directly.
"""

import re
from typing import Any

from app.rirekisho.schemas import EnglishEntry, ReadinessReport

# Without these a document is not a 履歴書 (FR-015). Named as the refusal names
# them, so a client can point at the same field either way.
REQUIRED = ("full_name_latin",)

# Identity fields the document has a box for, which stay blank when empty. The
# Japanese name is not here: 氏名 falls back to the Latin name, so it is never
# blank, only in English.
OPTIONAL_IDENTITY = ("furigana", "date_of_birth", "address", "phone", "email")

# Profile sections the document draws on, under the names the profile itself
# uses for them, so a client can link straight to the section to fill.
OPTIONAL_SECTIONS = ("education", "experiences", "certifications")

# Kana and kanji. An entry whose text has none will read as English on the page.
#
# Half-width katakana is in here because imported data is full of it: it is what
# older Japanese systems emit, and #002 reads documents produced by exactly those
# systems. Without it a name written only that way is reported as having no
# Japanese version, while the same name carrying two kanji is not (#107).
#
# Written as escapes with the block each range covers: as literal characters the
# pattern is a row of glyphs nobody can check against the standard.
_JAPANESE = re.compile(
    "["
    "\u3040-\u30ff"  # hiragana and katakana
    "\u3400-\u9fff"  # kanji, including extension A
    "\uf900-\ufaff"  # compatibility ideographs
    "\uff66-\uff9d"  # half-width katakana
    "]"
)


def missing_required(identity: Any | None) -> list[str]:
    """What the document cannot be produced without, as field names."""
    if identity is None:
        return ["identity"]
    return [
        f"identity.{field}" for field in REQUIRED if not _filled(getattr(identity, field, None))
    ]


def build_report(
    identity: Any | None,
    *,
    education: list[Any],
    experiences: list[Any],
    certifications: list[Any],
) -> ReadinessReport:
    required = missing_required(identity)

    optional = [
        f"identity.{field}"
        for field in OPTIONAL_IDENTITY
        if identity is None or not _filled(getattr(identity, field, None))
    ]
    sections = {
        "education": education,
        "experiences": experiences,
        "certifications": certifications,
    }
    optional += [name for name in OPTIONAL_SECTIONS if not sections[name]]

    return ReadinessReport(
        can_generate=not required,
        missing_required=required,
        missing_optional=optional,
        entries_without_japanese=_english_entries(education, experiences, certifications),
    )


def _english_entries(
    education: list[Any], experiences: list[Any], certifications: list[Any]
) -> list[EnglishEntry]:
    """Entries whose text on the page will be English.

    Judged from the text the document shows, not from the entry's recorded
    source language. That field defaults to English, so a Japanese institution
    entered without setting it would be reported as English — telling a user
    their own university has no Japanese version.
    """
    shown = [
        *(("education", e.id, e.institution) for e in education),
        *(("work_experience", e.id, e.employer_name) for e in experiences),
        *(("certification", e.id, e.name) for e in certifications),
    ]
    return [
        EnglishEntry(entry_id=entry_id, entry_type=entry_type, label=label)
        for entry_type, entry_id, label in shown
        if _filled(label) and not _JAPANESE.search(label)
    ]


def _filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True
