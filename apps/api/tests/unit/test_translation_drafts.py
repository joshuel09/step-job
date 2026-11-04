"""What the model boundary can and cannot hand back (feature 005, Phase 3).

A draft is a suggestion. Nothing stores one, nothing renders one, and it
reaches a resume only when a person approves it — so the tests here are not
about whether the English is good. They are about the shape of what comes
back, because the shape is what keeps a model's words out of a document
someone sends under their own name.

Two of them are worth reading as a pair:

- `TestWhatADraftCannotCarry` asserts there is no field for a seniority, a
  headcount or an outcome, so a provider cannot return one as *data*. It is
  worth being exact about what that buys, because it is easy to overstate:
  it keeps an embellishment from becoming a structured fact, and it does
  nothing about a model writing "Led a team of twelve" inside the rendering
  itself. No schema could — a translation has no passage to check it
  against. The review is the guarantee; this is a smaller, real thing.
- `TestAnAmbiguousPhrase` asserts the opposite kind of thing: that the
  product does *not* decide. 課長 is "Manager", "Section Chief" or
  "Department Head", and choosing one would make the product's word into a
  claim about someone's seniority (R-004).
"""

import re

import pytest
from app.ai.fake import FakeAIProvider, FakeBehaviour
from app.ai.provider import AIProvider, ProviderResponseInvalid, ProviderUnavailable
from app.ai.schemas import RenderingAlternative, TranslationDraft
from pydantic import ValidationError

JAPANESE = "課長としてビルド時間を半分にした"
UNAMBIGUOUS = "ビルドが遅かった"


def _draft(behaviour: FakeBehaviour | str = FakeBehaviour.extract, text: str = JAPANESE):
    return FakeAIProvider(behaviour).draft_translation(text, "ja", "en")


class TestAConfidentRendering:
    def test_it_renders_the_text_it_was_given(self):
        draft = _draft(text=UNAMBIGUOUS)
        assert draft.text == "The build was slow"

    def test_the_source_comes_back_with_it(self):
        """So the user compares the two rather than approving English against
        nothing. A draft shown alone asks someone to accept a translation of
        something they cannot see."""
        draft = _draft(text=UNAMBIGUOUS)
        assert draft.source_text == UNAMBIGUOUS

    def test_an_unambiguous_rendering_offers_no_alternatives(self):
        """Empty, not a single option. One option is not a choice, and
        offering it would train the user to click past the ones that are."""
        assert _draft(text=UNAMBIGUOUS).alternatives == []

    def test_the_fake_never_reaches_the_network(self, monkeypatch):
        """Every automated test uses this provider, so this is the property
        the rest of the suite rests on: continuous integration cannot depend
        on a paid external service, and a test whose outcome varies with a
        model's mood is not a test.

        Checked by making a socket impossible rather than by reading the
        source for suspicious words.
        """
        import socket

        def refuse(*args, **kwargs):
            raise AssertionError("the fake opened a socket")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)

        assert _draft(text=UNAMBIGUOUS).text == "The build was slow"


class TestAnAmbiguousPhrase:
    def test_the_choice_is_returned_rather_than_made(self):
        alternatives = _draft().alternatives
        assert [a.phrase for a in alternatives] == ["課長"]
        assert alternatives[0].options == ["Manager", "Section Chief", "Department Head"]

    def test_every_alternative_names_at_least_two_options(self):
        """The whole point of the field. An alternative with one option is a
        rendering wearing a choice's clothes."""
        for behaviour in (FakeBehaviour.extract, FakeBehaviour.whitespace_variant):
            for alternative in _draft(behaviour).alternatives:
                assert len(alternative.options) >= 2, alternative

    def test_the_schema_refuses_a_single_option(self):
        """Not left to the provider's good manners: a one-option alternative
        fails validation before any application code sees it."""
        with pytest.raises(ValidationError):
            RenderingAlternative(phrase="課長", options=["Manager"])

    @pytest.mark.parametrize(
        "options",
        [
            ["Manager", "Manager"],
            ["Manager", " Manager "],
            ["Manager", ""],
            ["", "   "],
            ["Manager", "Section Chief", ""],
            ["Manager", "Section Chief", "Manager"],
            ["Manager", "Section Chief", " Section Chief"],
        ],
        ids=[
            "identical",
            "identical-with-padding",
            "one-blank",
            "both-blank",
            "blank-among-three",
            "repeat-among-three",
            "repeat-among-three-with-padding",
        ],
    )
    def test_two_of_the_same_word_is_not_two_options(self, options):
        """Counting entries is not the rule. A user shown ["Manager",
        "Manager"] is being asked to choose and given nothing to choose
        between, which is worse than a confident draft — it looks as though
        the ambiguity was surfaced.

        The three-option cases are the ones that would slip through a check
        looking only for two survivors. A blank among three still shows the
        user an option that is not one, and clicking it approves an empty
        rendering.
        """
        with pytest.raises(ValidationError):
            RenderingAlternative(phrase="課長", options=options)

    def test_a_note_says_what_separates_them(self):
        note = _draft().alternatives[0].note
        assert note and "senior" in note.lower()

    def test_the_draft_uses_one_of_the_options_it_offers(self):
        """A rendering whose wording is not among the alternatives beside it
        asks the user to choose between three things, none of which is what
        they are looking at.

        Matched on a word boundary rather than with `in`: "Section Manager"
        contains "Manager", so a substring test would call a fourth invented
        title one of the three on offer. Catching that is the test.
        """
        draft = _draft()
        options = draft.alternatives[0].options
        used = [
            o
            for o in options
            if re.search(rf"(?<![A-Za-z ]){re.escape(o)}(?![A-Za-z])", draft.text)
        ]
        assert used, f"{draft.text!r} uses none of {options}"

    def test_a_phrase_absent_from_the_source_is_not_offered(self):
        """The alternatives describe this text, not a catalogue of everything
        the product knows is ambiguous."""
        assert _draft(text="部長として採用した").alternatives[0].phrase == "部長"
        assert "課長" not in {a.phrase for a in _draft(text="部長として採用した").alternatives}


class TestWhatADraftCannotCarry:
    """No field for a seniority, a headcount or an outcome.

    Which is not the same as "a model cannot embellish". It cannot return
    an embellishment as a *field* — something downstream could read, store
    or render as though the profile said it. It can still write one into
    the rendering, and the test below says so out loud rather than leaving
    the class name to imply otherwise.
    """

    FORBIDDEN = ("summary", "seniority", "headcount", "team_size", "outcome", "impact", "level")

    @pytest.mark.parametrize("field", FORBIDDEN)
    def test_the_schema_has_no_field_for_it(self, field):
        assert field not in TranslationDraft.model_fields

    def test_and_an_extra_one_is_not_quietly_accepted(self):
        """Pydantic ignores unknown keys by default, which would let a
        provider's extra field pass through unnoticed. It does not reach the
        model either way, but it should not survive the parse."""
        draft = TranslationDraft.model_validate(
            {"text": "Manager", "source_text": "課長", "seniority": "very senior"}
        )
        assert not hasattr(draft, "seniority")

    def test_the_fields_are_exactly_the_three(self):
        assert set(TranslationDraft.model_fields) == {"text", "source_text", "alternatives"}

    def test_but_the_rendering_itself_is_free_prose(self):
        """Stated as a test so the class above is not read as more than it
        is. This draft is an invention and the schema accepts it, because
        `text` is prose and nothing mechanical separates a rendering from a
        claim — unlike extraction, there is no passage to check against.

        What stops it reaching a resume is the person who reads the draft
        beside its source and does not approve it.
        """
        invented = TranslationDraft(text="Led a team of twelve", source_text="エンジニア")
        assert invented.text == "Led a team of twelve"


class TestWhenTheProviderFails:
    def test_an_outage_is_an_outage(self):
        """Worth returning for, and the user is told so."""
        with pytest.raises(ProviderUnavailable):
            _draft(FakeBehaviour.unavailable)

    def test_an_unusable_answer_is_not_an_outage(self):
        """The service is up and answering nonsense. Collapsing the two would
        leave the interface unable to say whether trying again is worth the
        user's time (FR-017b)."""
        with pytest.raises(ProviderResponseInvalid):
            _draft(FakeBehaviour.invalid)

    def test_a_transient_outage_clears(self):
        provider = FakeAIProvider(fail_times=1)
        with pytest.raises(ProviderUnavailable):
            provider.draft_translation(JAPANESE, "ja", "en")
        assert provider.draft_translation(JAPANESE, "ja", "en").text

    def test_a_blank_rendering_is_an_answer_and_not_an_error(self):
        """A provider that returns nothing has still answered. The refusal
        belongs where the approval is, not here (FR-025) — a draft of nothing
        is usable-looking and says nothing, which is the shape that needs
        catching later rather than the shape of an outage."""
        draft = _draft(FakeBehaviour.empty)
        assert draft.text == ""
        assert draft.source_text == JAPANESE


class TestTheBoundaryItself:
    def test_the_fake_still_satisfies_the_protocol(self):
        """T018's checkpoint. The protocol is runtime_checkable, so adding
        draft_translation to it broke conformance until this existed."""
        assert isinstance(FakeAIProvider(), AIProvider)

    def test_a_provider_is_handed_text_and_two_languages(self):
        """And not a profile, a session or an entry id. It proposes;
        deterministic code decides (R-003)."""
        import inspect

        signature = inspect.signature(FakeAIProvider.draft_translation)
        assert list(signature.parameters) == [
            "self",
            "text",
            "source_language",
            "target_language",
        ]


class TestTheEchoedSource:
    """The source text comes back from the provider, so it is checked.

    `source_text` is what the user compares the rendering against. A model
    that echoes a different passage would have the interface present that
    passage as the source of its English, and someone could approve a
    rendering against text they never wrote. The fake cannot get this wrong;
    a real provider can, so the concrete one checks.
    """

    def _provider(self, returns: TranslationDraft):
        from app.ai.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="unused-in-this-test", model="unused")
        provider._parse = lambda *args, **kwargs: returns  # type: ignore[method-assign]
        return provider

    def test_a_faithful_echo_is_returned(self):
        provider = self._provider(TranslationDraft(text="Manager", source_text="課長"))
        assert provider.draft_translation("課長", "ja", "en").text == "Manager"

    def test_a_different_passage_is_an_unusable_response(self):
        provider = self._provider(TranslationDraft(text="Manager", source_text="部長"))
        with pytest.raises(ProviderResponseInvalid):
            provider.draft_translation("課長", "ja", "en")

    def test_and_so_is_a_reworded_one(self):
        """Exact, not normalised. The prompt asks for the text back
        unchanged, and a provider that cannot manage that has got something
        else wrong too."""
        provider = self._provider(TranslationDraft(text="Manager", source_text=" 課長 "))
        with pytest.raises(ProviderResponseInvalid):
            provider.draft_translation("課長", "ja", "en")


class TestAnAlternativeForWordsNobodyWrote:
    """`phrase` is documented as appearing in the source exactly.

    An alternative for a phrase the user never wrote is a false choice: the
    interface cannot show it beside the source it is supposed to be part
    of, and the user is asked to decide about a term that is not theirs.
    Same rule as the echoed source, one level down.
    """

    def _provider(self, returns: TranslationDraft):
        from app.ai.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="unused-in-this-test", model="unused")
        provider._parse = lambda *args, **kwargs: returns  # type: ignore[method-assign]
        return provider

    def test_a_phrase_from_the_source_is_fine(self):
        provider = self._provider(
            TranslationDraft(
                text="Manager",
                source_text="課長",
                alternatives=[
                    RenderingAlternative(phrase="課長", options=["Manager", "Section Chief"])
                ],
            )
        )
        assert provider.draft_translation("課長", "ja", "en").alternatives[0].phrase == "課長"

    def test_a_phrase_that_is_not_is_an_unusable_response(self):
        provider = self._provider(
            TranslationDraft(
                text="Manager",
                source_text="課長",
                alternatives=[
                    RenderingAlternative(phrase="部長", options=["Director", "General Manager"])
                ],
            )
        )
        with pytest.raises(ProviderResponseInvalid):
            provider.draft_translation("課長", "ja", "en")

    def test_one_bad_phrase_among_good_ones_is_enough(self):
        """Not "most of them check out". Each one is a question put to the
        user, and one of them is about something they never wrote."""
        provider = self._provider(
            TranslationDraft(
                text="Manager and Senior Staff",
                source_text="課長と主任",
                alternatives=[
                    RenderingAlternative(phrase="課長", options=["Manager", "Section Chief"]),
                    RenderingAlternative(phrase="部長", options=["Director", "Head"]),
                ],
            )
        )
        with pytest.raises(ProviderResponseInvalid):
            provider.draft_translation("課長と主任", "ja", "en")

    @pytest.mark.parametrize("phrase", ["", "   ", "\n"], ids=["empty", "spaces", "newline"])
    def test_a_blank_phrase_is_refused_by_the_schema(self, phrase):
        """Where the rule belongs, rather than as a second condition on the
        membership check below.

        `"" in text` is true of every string, so a blank phrase sails
        through the very check that exists to catch a phrase the user never
        wrote — and the user is shown a choice about nothing.
        """
        with pytest.raises(ValidationError):
            RenderingAlternative(phrase=phrase, options=["Manager", "Section Chief"])

    def test_the_fake_only_offers_phrases_it_found(self):
        """Which is why the fake never trips this check: its alternatives
        come from scanning the source, not from a list it carries."""
        draft = _draft(text="課長としてビルド時間を半分にした")
        for alternative in draft.alternatives:
            assert alternative.phrase in draft.source_text
