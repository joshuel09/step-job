"""Turning source text into verified entries.

The order here is the whole point. A provider returns values with quoted
sources; the verifier drops every field whose quote is not in the document; only
what survives becomes an entry. Nothing downstream ever sees an unverified
value, so no later change can accidentally let one through by forgetting to
check.

An entry left with nothing after verification is discarded entirely — a proposal
with no fields is not a useful suggestion, it is noise.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.ai.provider import AIProvider
from app.ai.schemas import ExtractedEntryType
from app.imports import conflicts as conflict_detection
from app.imports.evidence import verify_entry

logger = logging.getLogger(__name__)

# Fields that must survive verification for an entry to be worth proposing.
# Without these a user is looking at a blank suggestion and cannot judge it.
REQUIRED_FIELDS: dict[ExtractedEntryType, tuple[str, ...]] = {
    ExtractedEntryType.work_experience: ("employer_name", "job_title"),
    ExtractedEntryType.education: ("institution",),
    ExtractedEntryType.certification: ("name",),
    ExtractedEntryType.skill: ("name",),
    ExtractedEntryType.language: ("language",),
}


@dataclass
class VerifiedEntry:
    """One entry whose every field is supported by the source."""

    entry_type: ExtractedEntryType
    values: dict[str, Any]
    evidence: dict[str, dict[str, str]]
    conflicts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExtractionOutcome:
    entries: list[VerifiedEntry] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    dropped_fields: int = 0
    dropped_entries: int = 0


def _dedupe_key(entry: VerifiedEntry) -> tuple:
    """What makes two extracted entries the same thing.

    FR-012: a document that describes one role twice — a summary repeating the
    detail below it — should propose it once.
    """
    values = entry.values
    if entry.entry_type is ExtractedEntryType.work_experience:
        return (
            entry.entry_type,
            str(values.get("employer_name", "")).strip().casefold(),
            str(values.get("job_title", "")).strip().casefold(),
            str(values.get("started_on", "")),
        )
    name = values.get("name") or values.get("institution") or values.get("language") or ""
    return (entry.entry_type, str(name).strip().casefold())


def extract(provider: AIProvider, source: str) -> ExtractionOutcome:
    """Read the source and return only what it actually supports.

    Provider failures are not caught here. Whether an outage is retried, and how
    it is reported, belongs to the import lifecycle — this function's job is the
    verification boundary.
    """
    result = provider.extract_career_information(source)
    outcome = ExtractionOutcome(not_found=[str(kind) for kind in result.not_found])

    seen: set[tuple] = set()

    for raw in result.entries:
        values, evidence = verify_entry(raw, source)
        outcome.dropped_fields += len(raw.fields) - len(values)

        required = REQUIRED_FIELDS.get(raw.entry_type, ())
        if not values or any(name not in values for name in required):
            # Everything that identified this entry failed verification. There is
            # nothing here a user could meaningfully judge.
            outcome.dropped_entries += 1
            continue

        values["source_language"] = str(raw.source_language)

        entry = VerifiedEntry(
            entry_type=raw.entry_type,
            values=values,
            evidence=evidence,
            conflicts=conflict_detection.detect(values),
        )

        key = _dedupe_key(entry)
        if key in seen:
            continue
        seen.add(key)

        outcome.entries.append(entry)

    _apply_cross_entry_conflicts(outcome)

    logger.info(
        "extraction verified",
        extra={
            "count": len(outcome.entries),
            "outcome": f"{outcome.dropped_fields} fields and "
            f"{outcome.dropped_entries} entries dropped as unverifiable",
        },
    )
    return outcome


def _apply_cross_entry_conflicts(outcome: ExtractionOutcome) -> None:
    experiences = [
        (index, entry)
        for index, entry in enumerate(outcome.entries)
        if entry.entry_type is ExtractedEntryType.work_experience
    ]
    if len(experiences) < 2:
        return

    found = conflict_detection.detect_across([entry.values for _, entry in experiences])
    for position, extra_conflicts in found.items():
        _, entry = experiences[position]
        entry.conflicts.extend(extra_conflicts)
