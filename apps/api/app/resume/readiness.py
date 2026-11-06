"""What a resume cannot be produced without.

One function for now, and the file exists so that User Story 2's fuller
report — the entries with no English version, the organisations with no
supplied name, the approvals whose source has changed — extends this rather
than starting a second answer to the same question.

Generation refuses by this same list, so the report a user reads before
generating and the refusal they would meet cannot disagree (FR-006).
"""

from collections.abc import Sequence
from typing import Any


def missing_required(identity: Any | None, experiences: Sequence[Any]) -> list[str]:
    """The two things a resume is not a resume without.

    A missing English version is **not** here. An entry with no approved
    translation renders as recorded, in Japanese, and the readiness route
    reports it — refusing to produce the document would be telling the user
    about a gap at the moment they can least do anything about it (FR-017,
    FR-020).
    """
    missing = []
    if identity is None or not (getattr(identity, "full_name_latin", "") or "").strip():
        missing.append("identity")
    if not experiences:
        missing.append("experiences")
    return missing
