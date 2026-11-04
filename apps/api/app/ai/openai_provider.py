"""The one concrete provider.

This is the only module in the project permitted to import a provider SDK
(constitution gate G12). Feature code depends on the protocol in `provider.py`;
if any other module imports this one directly, that gate has been broken and it
will be visible in the diff.

Provider errors are translated into the protocol's failure classes here, so that
the distinction between "the service is down" and "the service answered with
nonsense" survives the boundary — the interface needs it to tell a user whether
returning later is worth their time.
"""

import logging
from typing import TypeVar

from pydantic import BaseModel

from app.ai.provider import ProviderResponseInvalid, ProviderUnavailable
from app.ai.schemas import ExtractionResult, TranslationDraft
from app.core.settings import get_settings
from app.imports.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_input
from app.translations.prompts import TRANSLATION_SYSTEM_PROMPT, build_translation_input

logger = logging.getLogger(__name__)

_Parsed = TypeVar("_Parsed", bound=BaseModel)


class OpenAIProvider:
    """Requests structured output matching the schema of whatever was asked for."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.ai_model

        if not self._api_key:
            raise ValueError(
                "No provider key configured. Set AI_PROVIDER=fake for local work "
                "and continuous integration."
            )

    def _parse(self, system_prompt: str, user_input: str, schema: type[_Parsed]) -> _Parsed:
        """One request, with the two failure classes kept apart.

        Shared by both operations so the distinction between "the service is
        down" and "the service answered with nonsense" is made once. It is
        the distinction the interface needs to tell a user whether returning
        later is worth their time, and two copies of it would drift.
        """
        # Imported here rather than at module scope so that a missing SDK cannot
        # break an environment that only ever uses the fake.
        from openai import APIError, APITimeoutError, OpenAI, RateLimitError

        client = OpenAI(api_key=self._api_key)

        try:
            response = client.beta.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                response_format=schema,
            )
        except (RateLimitError, APITimeoutError) as error:
            raise ProviderUnavailable(str(error)) from error
        except APIError as error:
            # Connection and server-side errors are outages; everything else the
            # SDK raises here is the service answering unusably.
            status = getattr(error, "status_code", None)
            if status is None or status >= 500:
                raise ProviderUnavailable(str(error)) from error
            raise ProviderResponseInvalid(str(error)) from error

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ProviderResponseInvalid("provider returned no parsable result")
        return parsed

    def extract_career_information(self, text: str) -> ExtractionResult:
        result = self._parse(
            EXTRACTION_SYSTEM_PROMPT, build_extraction_input(text), ExtractionResult
        )
        logger.info("extraction returned", extra={"count": len(result.entries)})
        return result

    def draft_translation(
        self, text: str, source_language: str, target_language: str
    ) -> TranslationDraft:
        """Ask for a rendering of this text and nothing beyond it.

        The schema is the request: `TranslationDraft` has a field for the
        rendering, a field for the source it renders, and a field for the
        phrases that could go more than one way. There is no field for a
        summary or a seniority, so structured output cannot return one.
        """
        draft = self._parse(
            TRANSLATION_SYSTEM_PROMPT,
            build_translation_input(text, source_language, target_language),
            TranslationDraft,
        )

        # The echo is what the user compares the rendering against. A model
        # that returns a different passage has answered a question nobody
        # asked, and the draft would present that passage as the source of
        # its English — so a mismatch is an unusable response, not a draft.
        # Exact, not normalised: the prompt asks for the text back unchanged,
        # and a provider that cannot manage that has got something else wrong.
        if draft.source_text != text:
            raise ProviderResponseInvalid(
                "provider echoed a source text that is not the text it was given"
            )

        # Same rule, one level down. `phrase` is documented as appearing in
        # the source exactly, and an alternative for words the user never
        # wrote is a false choice: the interface cannot show it beside the
        # source, and the user is asked to decide about a term that is not
        # theirs.
        for alternative in draft.alternatives:
            if alternative.phrase not in text:
                raise ProviderResponseInvalid(
                    "provider offered an alternative for a phrase that is not in the source"
                )

        logger.info(
            "translation drafted",
            extra={
                "source_language": source_language,
                "target_language": target_language,
                "alternatives": len(draft.alternatives),
            },
        )
        return draft
