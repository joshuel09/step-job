"""Request models for the English resume, matching contracts/openapi.yaml.

Two options, and both are about the paper rather than the words. What is
*not* offered is as deliberate:

- No ordering. An English resume is reverse-chronological, and offering the
  choice would imply the other is conventional somewhere.
- No date convention. This document is Western-dated throughout (FR-004),
  and a 和暦 option would be a setting that must never be switched on.
"""

import enum

from pydantic import BaseModel


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
