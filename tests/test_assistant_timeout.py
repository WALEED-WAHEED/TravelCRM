"""The AI assistant must fail gracefully (not with a server error) when Gemini times out."""
from unittest import mock

import httpx
import pytest

from assistant import llm


def test_timeout_becomes_a_provider_error(settings):
    settings.GEMINI_API_KEY = "test-key-not-placeholder"
    client = llm.GeminiClient()
    with mock.patch.object(client._client.models, "generate_content", side_effect=httpx.ReadTimeout("slow")):
        with pytest.raises(llm.AssistantProviderError):
            client.generate("system", [{"role": "user", "content": "hi"}], [])
