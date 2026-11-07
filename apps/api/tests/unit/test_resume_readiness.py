"""The shape of the readiness report, where the shape is the rule.

The route tests cover what a profile produces. These cover the two claims
that are true of the module rather than of any one profile, and that a
later change could break without any existing test noticing.
"""

import inspect
import uuid
from datetime import UTC, datetime

from app.resume import readiness
from app.resume.schemas import StoredTranslation
from app.translations.models import TRANSLATABLE_FIELDS, TranslatableEntry


class TestWhatThisDocumentReports:
    def test_a_career_story_is_not_among_the_fields(self):
        """Stories are translatable and the 職務経歴書 prints them. An
        English resume has no section for one, so reporting a story as
        something this document lacks would send the user off to do work
        that changes nothing on the page."""
        assert TranslatableEntry.career_story in TRANSLATABLE_FIELDS
        assert TranslatableEntry.career_story not in readiness.RENDERED_FIELDS

    def test_the_report_is_not_even_given_them(self):
        """The stronger half: there is no parameter a story could arrive
        through, so excluding them is not a filter anyone can forget."""
        assert "stories" not in inspect.signature(readiness.build_report).parameters

    def test_every_reported_field_is_one_that_could_be_stored(self):
        """A field reported as needing English that the approval route
        refuses would be an invitation the product then declines."""
        for entry_type, fields in readiness.RENDERED_FIELDS.items():
            assert set(fields) <= set(TRANSLATABLE_FIELDS[entry_type]), entry_type

    def test_every_reported_type_can_be_named_to_the_user(self):
        """An entry reported without a label is a row the interface can
        only show as an id."""
        assert set(readiness.RENDERED_FIELDS) <= set(readiness.LABELS)


class TestWhatTheReportLeavesOut:
    """The structural guards above are read off the module's own constants,
    so each would pass after a matching edit. These call `build_report` and
    look at what comes back."""

    def _stored(self, entry_type: TranslatableEntry, field: str) -> StoredTranslation:
        return StoredTranslation(
            id=uuid.uuid4(),
            entry_type=entry_type,
            entry_id=uuid.uuid4(),
            field=field,
            text="Halved the build time",
            approved_at=datetime.now(UTC),
            is_stale=True,
            source_text="ビルド時間を半分にした",
        )

    def test_a_stale_story_approval_is_not_reported(self):
        """Approvals belong to the profile, not to one document, so a story
        reaches this report through `stored` even though no story reaches it
        through the entries. The 職務経歴書 keeps and prints that English;
        a resume's reader has no page to compare it against."""
        report = readiness.build_report(
            None, stored=[self._stored(TranslatableEntry.career_story, "title")]
        )

        assert report.stale_translations == []

    def test_a_stale_approval_this_document_prints_is(self):
        """The distinguishing half. A report that dropped every stale
        approval would pass the test above and tell the user nothing."""
        report = readiness.build_report(
            None, stored=[self._stored(TranslatableEntry.work_experience, "job_title")]
        )

        assert [row.field for row in report.stale_translations] == ["job_title"]

    def test_an_approval_that_still_matches_is_not_reported(self):
        fresh = self._stored(TranslatableEntry.work_experience, "job_title")

        report = readiness.build_report(
            None, stored=[fresh.model_copy(update={"is_stale": False, "source_text": None})]
        )

        assert report.stale_translations == []
