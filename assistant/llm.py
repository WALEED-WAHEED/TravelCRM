"""
Provider-agnostic LLM client. Every provider adapter (Gemini today,
OpenAI/Claude later) speaks the same generic ToolSpec/ToolCall/LLMResponse
shapes so the orchestration in assistant/engine.py never touches an SDK
directly — switching providers later is a matter of adding one adapter
class and flipping AI_PROVIDER in settings.
"""
from dataclasses import dataclass, field

import httpx
from django.conf import settings


class AssistantNotConfigured(Exception):
    """Raised when the configured provider has no usable API key yet
    (e.g. still the dummy placeholder) — callers should show a clear,
    friendly message rather than let this surface as a stack trace."""


class AssistantProviderError(Exception):
    """Raised when the provider API call itself fails (bad key, quota
    exceeded, network error, etc.)."""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema, e.g. {"type": "object", "properties": {...}, "required": [...]}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list = field(default_factory=list)  # list[ToolCall]


class LLMClient:
    def generate(self, system_prompt, messages, tools):
        """`messages` is a list of dicts, each one of:
        {'role': 'user', 'content': str}
        {'role': 'assistant', 'content': str}
        {'role': 'assistant', 'tool_calls': [ToolCall, ...]}
        {'role': 'tool', 'tool_call_id': str, 'name': str, 'content': dict}
        `tools` is a list[ToolSpec]. Returns an LLMResponse."""
        raise NotImplementedError


class GeminiClient(LLMClient):
    _PLACEHOLDER_VALUES = {"", "dummy-placeholder-replace-me"}

    def __init__(self):
        if settings.GEMINI_API_KEY in self._PLACEHOLDER_VALUES:
            raise AssistantNotConfigured(
                "GEMINI_API_KEY is still the placeholder value — add a real key from "
                "https://aistudio.google.com to your .env to enable the assistant."
            )
        from google import genai
        self._genai = genai
        from google.genai import types
        # Bounded: a stuck Gemini request must not hold a web worker for minutes (it runs inside the request).
        self._client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(getattr(settings, "GEMINI_TIMEOUT_MS", 30000))),
        )
        self._model = settings.GEMINI_MODEL

    def _to_contents(self, messages):
        from google.genai import types
        contents = []
        for m in messages:
            role = m['role']
            if role == 'user':
                contents.append(types.Content(role='user', parts=[types.Part(text=m['content'])]))
            elif role == 'assistant':
                if m.get('tool_calls'):
                    parts = [
                        types.Part(function_call=types.FunctionCall(name=tc.name, args=tc.arguments))
                        for tc in m['tool_calls']
                    ]
                    contents.append(types.Content(role='model', parts=parts))
                else:
                    contents.append(types.Content(role='model', parts=[types.Part(text=m.get('content', ''))]))
            elif role == 'tool':
                contents.append(types.Content(role='user', parts=[
                    types.Part(function_response=types.FunctionResponse(name=m['name'], response=m['content']))
                ]))
        return contents

    def generate(self, system_prompt, messages, tools):
        from google.genai import errors as genai_errors
        from google.genai import types

        contents = self._to_contents(messages)
        genai_tools = None
        if tools:
            genai_tools = [types.Tool(function_declarations=[
                types.FunctionDeclaration(name=t.name, description=t.description, parameters_json_schema=t.parameters)
                for t in tools
            ])]

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=genai_tools,
                ),
            )
        except genai_errors.APIError as e:
            raise AssistantProviderError(str(e)) from e
        except (httpx.TimeoutException, httpx.TransportError) as e:
            # Timed out or couldn't reach Gemini: same friendly path as an API error, not a 500.
            raise AssistantProviderError(f"Gemini did not respond in time ({type(e).__name__}).") from e

        tool_calls = []
        for i, fc in enumerate(response.function_calls or []):
            tool_calls.append(ToolCall(id=f"{fc.name}-{i}", name=fc.name, arguments=dict(fc.args or {})))

        return LLMResponse(text=response.text or "", tool_calls=tool_calls)


_PROVIDERS = {
    'gemini': GeminiClient,
}


def get_llm_client():
    provider = settings.AI_PROVIDER
    provider_cls = _PROVIDERS.get(provider)
    if provider_cls is None:
        raise AssistantNotConfigured(f"Unknown AI_PROVIDER '{provider}'.")
    return provider_cls()
