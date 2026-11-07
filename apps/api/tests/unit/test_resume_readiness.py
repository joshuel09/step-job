"""The shape of the readiness report, where the shape is the rule.

The route tests cover what a profile produces. These cover the two claims
that are true of the module rather than of any one profile, and that a
later change could break without any existing test noticing.
"""

import inspect

from app.resume import readiness
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
