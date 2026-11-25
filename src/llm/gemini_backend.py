from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable

from google import genai
from google.genai import errors, types

from src.llm.base import LLMError, LLMReply, run_tool

log = logging.getLogger(__name__)


class GeminiLLM:
    def __init__(self, model: str, *, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise LLMError("Prod mode needs GEMINI_API_KEY (or GOOGLE_API_KEY) to be set.")
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def chat(self, system: str, messages: list[dict[str, Any]], *,
             json_schema: dict[str, Any] | None = None,
             temperature: float = 0.0) -> LLMReply:
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
        if json_schema is not None:
            config.response_mime_type = "application/json"
            config.response_json_schema = json_schema
        response, elapsed = self._call(_to_contents(messages), config)
        return self._reply(response, elapsed)

    def chat_with_tools(self, system: str, messages: list[dict[str, Any]],
                        tools: list[Callable[..., str]], *, max_rounds: int = 6,
                        temperature: float = 0.0) -> LLMReply:
        # Run the tool loop ourselves (SDK auto-calling off) so behavior matches
        # the Ollama backend: same round limit, same error handling, same tracking.
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        by_name = {t.__name__: t for t in tools}
        contents = _to_contents(messages)
        called: list[str] = []

        for _ in range(max_rounds):
            response, elapsed = self._call(contents, config)
            calls = response.function_calls or []
            if not calls:
                reply = self._reply(response, elapsed)
                reply.tool_calls_made = called
                return reply

            contents.append(response.candidates[0].content)
            parts = []
            for call in calls:
                args = dict(call.args or {})
                called.append(call.name)
                result = run_tool(by_name, call.name, args)
                log.debug("tool %s(%s) -> %s", call.name, args, result[:200])
                parts.append(types.Part.from_function_response(
                    name=call.name, response={"result": result}))
            contents.append(types.Content(role="user", parts=parts))

        raise LLMError(f"Model kept calling tools after {max_rounds} rounds: {called}")

    def _call(self, contents: list[types.Content], config: types.GenerateContentConfig):
        start = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=contents, config=config)
        except errors.APIError as exc:
            raise LLMError(f"Gemini error ({exc.code}): {exc.message}") from exc
        elapsed = time.perf_counter() - start

        candidate = response.candidates[0] if response.candidates else None
        if candidate is None:
            raise LLMError(f"Gemini returned no answer: {response.prompt_feedback}")
        if candidate.finish_reason == types.FinishReason.MAX_TOKENS:
            raise LLMError("Gemini output was cut off (MAX_TOKENS).")
        return response, elapsed

    def _reply(self, response: Any, elapsed: float) -> LLMReply:
        text = (response.text or "").strip()
        if not text:
            raise LLMError("Model returned an empty response.")
        usage = response.usage_metadata
        reply = LLMReply(text=text, model=self.model,
                         prompt_tokens=usage.prompt_token_count if usage else None,
                         output_tokens=usage.candidates_token_count if usage else None,
                         seconds=round(elapsed, 1))
        log.info("LLM %s: %s in / %s out tokens, %.1fs", reply.model,
                 reply.prompt_tokens, reply.output_tokens, reply.seconds)
        return reply


def _to_contents(messages: list[dict[str, Any]]) -> list[types.Content]:
    # Gemini calls the assistant role "model"
    return [
        types.Content(role="model" if m["role"] == "assistant" else "user",
                      parts=[types.Part.from_text(text=m["content"])])
        for m in messages
    ]
