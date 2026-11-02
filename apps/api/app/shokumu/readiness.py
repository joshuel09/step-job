"""What a 職務経歴書 would lack, said before it is printed rather than after.

A pure function from what the profile holds to a report, in three parts that
need three different responses from the user:

- **missing_required**: without these there is no document. Generation refuses,
  and it refuses using this same rule, so the report and the refusal cannot
  disagree about whether a document can be made (FR-006).
- **missing_optional**: these sections will simply be empty. The document is
  still produced; the user learns now that a heading will have nothing under
  it (FR-013).
- **unattached_achievements**: these appear in the closing section rather than
  under an employer. Nothing here is missing — it is all in the document — but
  a user who meant to attach one and did not should find out before they send
  it, not after. Nothing is guessed on their behalf (R-005).

Like the section projection, it knows nothing about PDFs and touches no
database, so every case can be tested directly.
"""

from collections.abc import Sequence
from typing import Any

from app.shokumu.schemas import ReadinessReport, UnattachedAchievement

# Sections the document draws, under the names the profile uses for them, so a
# client can link straight to the section to fill. Education is not here: a
# 職務経歴書 is work history, and education belongs to the 履歴書.
OPTIONAL_SECTIONS = ("skills", "languages", "certifications", "stories")


def missing_required(identity: Any | None, experiences: Sequence[Any]) -> list[str]:
    """What the document cannot be produced without.

    Two things, and generation refuses by this same list. A 職務経歴書 with no
    career history is not a sparse document; it is a different one.
    """
    missing = []
    if identity is None or not (getattr(identity, "full_name_latin", "") or "").strip():
        missing.append("identity")
    if not experiences:
        missing.append("experiences")
    return missing


def build_report(
    identity: Any | None,
    *,
    experiences: Sequence[Any],
    stories: Sequence[Any] = (),
    skills: Sequence[Any] = (),
    languages: Sequence[Any] = (),
    certifications: Sequence[Any] = (),
) -> ReadinessReport:
    required = missing_required(identity, experiences)

    held = {
        "skills": skills,
        "languages": languages,
        "certifications": certifications,
        "stories": stories,
    }
    optional = [name for name in OPTIONAL_SECTIONS if not held[name]]

    known = {entry.id for entry in experiences}
    return ReadinessReport(
        can_generate=not required,
        missing_required=required,
        missing_optional=optional,
        unattached_achievements=[
            UnattachedAchievement(entry_id=story.id, title=story.title)
            for story in stories
            if story.work_experience_id is None or story.work_experience_id not in known
        ],
    )
