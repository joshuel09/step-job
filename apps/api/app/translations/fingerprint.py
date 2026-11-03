"""A digest of the source text, as it read when the user approved a rendering.

An approved English version describes a particular Japanese sentence. Change
that sentence and the approval still exists, but it no longer describes
anything the profile holds — so the user has to be told, rather than sending
a document whose English says what they used to mean (FR-023).

Detecting that needs a value taken at approval and compared later, which is
the whole reason the fingerprint is stored beside the text rather than
computed when it is wanted.

Stable across processes, deliberately. Python's own `hash()` is salted per
interpreter, so an approval taken before a restart would read as stale after
one, and every user would be asked to re-approve work they had already
approved every time the application was deployed.
"""

import hashlib
import unicodedata


def fingerprint(source: str) -> str:
    """The digest of a source string.

    Normalised to NFC first, because the same Japanese can arrive composed or
    decomposed depending on the keyboard and the operating system that typed
    it, and two spellings of one character are not a change the user made.

    Nothing else is normalised. Whitespace in particular is kept as it is: a
    user who fixed the spacing in a sentence changed it, and an approval of
    the old spacing should be seen to be of the old spacing.
    """
    return hashlib.sha256(unicodedata.normalize("NFC", source).encode("utf-8")).hexdigest()


def is_stale(stored: str, source: str) -> bool:
    """Whether an approval taken against `stored` still describes `source`."""
    return stored != fingerprint(source)
