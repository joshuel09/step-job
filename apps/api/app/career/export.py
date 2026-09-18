"""Exporting a profile.

One archive holding two things (FR-035): a structured file carrying every entry
and the relationships between them, and a readable document of the same profile
for a person to open. Shipping only one of these fails one of the two audiences —
portability needs the data, and most users cannot read it.

Japan-specific fields are included regardless of their disclosure settings
(FR-037): those settings govern what may appear in a generated document, not what
the user may hold of their own data.

Nothing is retained server-side (research.md R-005). A stored export would be a
second copy of the most sensitive data in the product, outliving the deletion
guarantees in deletion.py.
"""

import io
import json
import zipfile
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.career import models, service


def _value(v: Any) -> Any:
    if isinstance(v, date | datetime):
        return v.isoformat()
    return str(v) if hasattr(v, "hex") else v


def _row(entry: Any) -> dict[str, Any]:
    return {
        column.name: _value(getattr(entry, column.name))
        for column in entry.__table__.columns
    }


def build_payload(session: Session, profile: models.CareerProfile) -> dict[str, Any]:
    """Every entry the user holds, with nothing summarised away (FR-036)."""
    payload: dict[str, Any] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": _row(profile),
    }

    for name, model in (
        ("identity", models.Identity),
        ("japan", models.JapanProfile),
        ("preferences", models.CareerPreference),
    ):
        entry = service.get_singleton(session, profile, model)
        payload[name] = _row(entry) if entry else None

    for name in service.SECTION_MODELS:
        payload[name] = [_row(e) for e in service.list_entries(session, profile, name)]

    payload["stories"] = [
        _row(s)
        for s in session.query(models.CareerStory)
        .filter(models.CareerStory.profile_id == profile.id)
        .all()
    ]
    return payload


def _readable(payload: dict[str, Any]) -> str:
    lines: list[str] = ["# Career profile", "", f"Exported {payload['exported_at']}", ""]

    identity = payload.get("identity")
    if identity:
        lines += ["## Name", identity.get("full_name_latin", ""), ""]

    if payload.get("experiences"):
        lines.append("## Work experience")
        for e in payload["experiences"]:
            ended = e.get("ended_on") or "present"
            lines.append(f"- {e['job_title']}, {e['employer_name']} ({e['started_on']} – {ended})")
            if e.get("description"):
                lines.append(f"  {e['description']}")
        lines.append("")

    for title, key, fmt in (
        (
            "Education",
            "education",
            lambda x: f"- {x['institution']} {x.get('qualification') or ''}".rstrip(),
        ),
        ("Certifications", "certifications", lambda x: f"- {x['name']}"),
        ("Skills", "skills", lambda x: f"- {x['name']}"),
        ("Languages", "languages", lambda x: f"- {x['language']} ({x['proficiency']})"),
    ):
        if payload.get(key):
            lines.append(f"## {title}")
            lines += [fmt(item) for item in payload[key]]
            lines.append("")

    if payload.get("stories"):
        lines.append("## Career stories")
        for s in payload["stories"]:
            lines += [
                f"### {s['title']}",
                f"Challenge: {s['challenge']}",
                f"Action: {s['action']}",
                f"Result: {s['result']}",
                "",
            ]

    return "\n".join(lines)


def build_archive(session: Session, profile: models.CareerProfile) -> bytes:
    payload = build_payload(session, profile)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("profile.json", json.dumps(payload, indent=2, ensure_ascii=False))
        archive.writestr("profile.md", _readable(payload))
    return buffer.getvalue()
