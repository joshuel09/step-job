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

from app.ai.provider import ProviderResponseInvalid, ProviderUnavailable
from app.ai.schemas import ExtractionResult
from app.core.settings import get_settings
from app.imports.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_input

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Requests structured output matching `ExtractionResult`."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.ai_model

        if not self._api_key:
            raise ValueError(
                "No provider key configured. Set AI_PROVIDER=fake for local work "
                "and continuous integration."
            )

    def extract_career_information(self, text: str) -> ExtractionResult:
        # Imported here rather than at module scope so that a missing SDK cannot
        # break an environment that only ever uses the fake.
        from openai import APIError, APITimeoutError, OpenAI, RateLimitError

        client = OpenAI(api_key=self._api_key)

        try:
            response = client.beta.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": build_extraction_input(text)},
                ],
                response_format=ExtractionResult,
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

        logger.info("extraction returned", extra={"count": len(parsed.entries)})
        return parsed
