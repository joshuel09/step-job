"""What the English resume routes take and return, per contracts/openapi.yaml.

The request offers two options, and both are about the paper rather than
the words. What is *not* offered is as deliberate:

- No ordering. An English resume is reverse-chronological, and offering the
  choice would imply the other is conventional somewhere.
- No date convention. This document is Western-dated throughout (FR-004),
  and a 和暦 option would be a setting that must never be switched on.
"""

import enum
import uuid

from pydantic import BaseModel

from app.translations.models import NamedEntry
from app.translations.schemas import EntryField, StoredTranslation


class PaperSize(enum.StrEnum):
    """US Letter by default.

    The document follows a US convention and is most often printed or
    screened on Letter. A4 is offered because a user in Japan applying to a
    foreign-affiliated employer may need it (FR-022).
    """

    letter = "letter"
    a4 = "a4"


class ResumeRequest(BaseModel):
    """What the user chose. Neither option changes what the document says."""

    paper_size: PaperSize = PaperSize.letter

    # Shortening a resume is the user choosing what to leave out, never the
    # system dropping entries to fit (FR-007). Skills is the section most
    # often cut, so it is the one with a switch.
    include_skills: bool = True


class UntranslatedField(EntryField):
    """An entry with no stored English version of one of its fields.

    Carries enough to act on without a second request: which field, how to
    name the entry to the user, and the text itself. A report that named
    only ids would send the interface back for every row it wanted to
    show.
    """

    #: How to name this entry to the user — the employer, the institution.
    #: Not the field's own text, which is `source_text`: "担当業務" under a
    #: heading of "担当業務" tells the user nothing about which role it is.
    label: str
    source_text: str


class UntranslatedName(BaseModel):
    """An organisation with no English name supplied.

    Separate from `UntranslatedField` because the answer is different.
    Nothing drafts these: 株式会社サンプル's English name is whatever that
    company calls itself, and a transliteration is a guess (FR-021, R-002).
    The user supplies it or the Japanese stands on the page, which is why
    this document still embeds a CJK font.
    """

    entry_type: NamedEntry
    entry_id: uuid.UUID

    #: Which name, since a certification has two — `name` and `issuer`.
    field: str
    recorded_name: str


class ResumeReadinessReport(BaseModel):
    """What a resume would lack, said before it is produced (FR-020).

    Four lists rather than one, because they need four different responses
    from the user: something to fill in, something to draft, something to
    look up, and something to re-read. Merging them would leave the
    interface sorting out which was which.
    """

    #: False only when something essential is absent (FR-006). A missing
    #: English version is never essential: the entry appears as recorded,
    #: and refusing the document would be telling the user about a gap at
    #: the moment they can least do anything about it (FR-017).
    can_generate: bool
    missing_required: list[str] = []
    needs_english: list[UntranslatedField] = []
    untranslated_names: list[UntranslatedName] = []

    #: Approvals whose source has changed since. Reported, never
    #: re-drafted and never discarded: the user approved those words, and a
    #: typo fix in the Japanese does not withdraw that (FR-023).
    stale_translations: list[StoredTranslation] = []
