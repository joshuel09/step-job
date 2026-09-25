"""Provider selection.

Feature code asks for a provider here and receives one satisfying the protocol.
It never names a concrete implementation, which is what keeps constitution gate
G12 checkable: an import of `openai_provider` anywhere outside this module is a
visible breach.

The fake is the default. Reaching the network has to be something a deployment
opts into, not something a forgotten setting does by accident.
"""

from app.ai.provider import (
    AIError,
    AIProvider,
    NoExtractableContent,
    ProviderResponseInvalid,
    ProviderUnavailable,
)
from app.core.settings import get_settings

__all__ = [
    "AIError",
    "AIProvider",
    "NoExtractableContent",
    "ProviderResponseInvalid",
    "ProviderUnavailable",
    "get_provider",
]


def get_provider() -> AIProvider:
    name = get_settings().ai_provider.lower()

    if name == "fake":
        from app.ai.fake import FakeAIProvider

        return FakeAIProvider()

    if name == "openai":
        from app.ai.openai_provider import OpenAIProvider

        return OpenAIProvider()

    raise ValueError(f"Unknown AI provider: {name!r}. Use 'fake' or 'openai'.")
