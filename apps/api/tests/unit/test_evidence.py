"""The evidence verifier.

This is the enforcement of Principle IV, so these are the tests that matter most
in this feature. If they are weakened, nothing else in the system prevents a
fabricated value reaching a user's resume.

The near-miss cases are deliberate. A fabricated quote is usually plausible —
that is what makes it a fabrication rather than noise — so any check that
tolerates "close enough" rewards exactly the thing it exists to catch.
"""

import pytest
from app.ai.fake import FakeAIProvider, FakeBehaviour
from app.imports.evidence import normalise, quote_is_supported, verify_fields

SOURCE = "Software Engineer, Example Corp. April 2021 to March 2024."


class TestQuoteIsSupported:
    def test_an_exact_passage_is_supported(self):
        assert quote_is_supported("Software Engineer", SOURCE)

    def test_the_whole_source_is_supported(self):
        assert quote_is_supported(SOURCE, SOURCE)

    def test_a_passage_absent_from_the_source_is_not(self):
        assert not quote_is_supported("Director of Engineering", SOURCE)

    def test_an_empty_quote_is_not_supported(self):
        assert not quote_is_supported("", SOURCE)

    def test_whitespace_only_is_not_supported(self):
        assert not quote_is_supported("   \n  ", SOURCE)

    def test_a_trivially_short_quote_is_not_supported(self):
        # Two characters match almost any document and evidence almost nothing.
        assert not quote_is_supported("So", SOURCE)

    @pytest.mark.parametrize(
        "quote",
        [
            "Software\nEngineer",
            "Software   Engineer",
            "  Software Engineer  ",
            "Software\t Engineer",
        ],
    )
    def test_whitespace_differences_are_tolerated(self, quote):
        # Extracted document text routinely differs from the original in line
        # breaks and spacing. A correct extraction must not fail over a newline.
        assert quote_is_supported(quote, SOURCE)

    def test_case_differences_are_tolerated(self):
        assert quote_is_supported("SOFTWARE ENGINEER", SOURCE)

    def test_a_near_miss_is_not_supported(self):
        # One word different. Fuzzy matching would let this through, which is
        # precisely why there is none.
        assert not quote_is_supported("Software Architect", SOURCE)

    def test_a_reordered_passage_is_not_supported(self):
        assert not quote_is_supported("Engineer Software", SOURCE)

    def test_a_passage_from_a_different_document_is_not_supported(self):
        assert not quote_is_supported("Senior Developer, Other Corp", SOURCE)

    def test_full_width_characters_match_their_ascii_equivalents(self):
        japanese_source = "エンジニア、サンプル株式会社。ＰＨＰ経験あり。"
        assert quote_is_supported("PHP経験あり", japanese_source)


class TestNormalise:
    def test_collapses_whitespace_and_folds_case(self):
        assert normalise("  Software\n\n  ENGINEER ") == "software engineer"

    def test_is_stable_across_unicode_forms(self):
        assert normalise("ＰＨＰ") == normalise("PHP")


class TestVerifyFields:
    def _fields(self, behaviour: FakeBehaviour):
        result = FakeAIProvider(behaviour).extract_career_information(SOURCE)
        return result.entries[0].fields

    def test_an_honest_extraction_survives_with_its_evidence(self):
        values, evidence = verify_fields(self._fields(FakeBehaviour.extract), SOURCE)

        assert "job_title" in values
        assert evidence["job_title"]["quote"] in SOURCE
        assert evidence["job_title"]["verified"] is True

    def test_a_fabricated_field_is_dropped_entirely(self):
        values, evidence = verify_fields(self._fields(FakeBehaviour.fabricate), SOURCE)

        # Dropped, not flagged. A value shown with a warning is still a value
        # someone might accept.
        assert values == {}
        assert evidence == {}

    def test_a_field_with_no_quote_is_dropped(self):
        values, evidence = verify_fields(self._fields(FakeBehaviour.quote_missing), SOURCE)

        assert values == {}
        assert evidence == {}

    def test_a_near_miss_is_dropped(self):
        values, _ = verify_fields(self._fields(FakeBehaviour.near_miss), SOURCE)

        assert values == {}

    def test_a_whitespace_variant_survives(self):
        values, evidence = verify_fields(self._fields(FakeBehaviour.whitespace_variant), SOURCE)

        assert "job_title" in values
        assert evidence["job_title"]["verified"] is True

    def test_every_surviving_field_has_evidence(self):
        """The invariant: a value in the profile always has a passage behind it."""
        values, evidence = verify_fields(self._fields(FakeBehaviour.extract), SOURCE)

        assert set(values) == set(evidence)
        for name, record in evidence.items():
            assert quote_is_supported(record["quote"], SOURCE), name

    def test_no_fields_at_all_is_not_an_error(self):
        assert verify_fields({}, SOURCE) == ({}, {})
