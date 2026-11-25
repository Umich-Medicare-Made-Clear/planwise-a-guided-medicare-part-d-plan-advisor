from __future__ import annotations

import logging
import time
from typing import Any, Callable

from ollama import Client, ResponseError

from src.llm.base import LLMError, LLMReply, run_tool

log = logging.getLogger(__name__)


class OllamaLLM:
    def __init__(self, model: str, *, num_ctx: int = 16384, host: str | None = None,
                 timeout: float = 900.0) -> None:
        self.model = model
        # Ollama's default context is small and it silently drops the start of
        # the prompt when it overflows (i.e. the report rules), so set it explicitly.
        self.num_ctx = num_ctx
        self.client = Client(host=host, timeout=timeout)

    def chat(self, system: str, messages: list[dict[str, Any]], *,
             json_schema: dict[str, Any] | None = None,
             temperature: float = 0.0) -> LLMReply:
        response, elapsed = self._call(system, messages, format=json_schema,
                                       temperature=temperature)
        return self._reply(response, elapsed, response.message.content or "")

    def chat_with_tools(self, system: str, messages: list[dict[str, Any]],
                        tools: list[Callable[..., str]], *, max_rounds: int = 6,
                        temperature: float = 0.0) -> LLMReply:
        by_name = {t.__name__: t for t in tools}
        convo = list(messages)
        called: list[str] = []

        for _ in range(max_rounds):
            response, elapsed = self._call(system, convo, tools=tools, temperature=temperature)
            msg = response.message
            if not msg.tool_calls:
                reply = self._reply(response, elapsed, msg.content or "")
                reply.tool_calls_made = called
                return reply

            convo.append(msg)
            for call in msg.tool_calls:
                name, args = call.function.name, dict(call.function.arguments or {})
                called.append(name)
                result = run_tool(by_name, name, args)
                log.debug("tool %s(%s) -> %s", name, args, result[:200])
                convo.append({"role": "tool", "tool_name": name, "content": result})

        raise LLMError(f"Model kept calling tools after {max_rounds} rounds: {called}")

    def _call(self, system: str, messages: list[Any], *, temperature: float = 0.0,
              **kwargs: Any):
        start = time.perf_counter()
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "system", "content": system}, *messages],
                options={"temperature": temperature, "num_ctx": self.num_ctx},
                **kwargs,
            )
        except ResponseError as exc:
            hint = f" Run `ollama pull {self.model}`." if exc.status_code == 404 else ""
            raise LLMError(f"Ollama error ({exc.status_code}): {exc.error}.{hint}") from exc
        except ConnectionError as exc:
            raise LLMError("Cannot reach Ollama. Is the Ollama app running?") from exc
        elapsed = time.perf_counter() - start

        if response.done_reason == "length":
            raise LLMError(f"Output was cut off (num_ctx={self.num_ctx}). Raise PLANWISE_NUM_CTX.")
        if (response.prompt_eval_count or 0) >= self.num_ctx - 64:
            log.warning("Prompt used %s of %s context tokens; the start may have been dropped.",
                        response.prompt_eval_count, self.num_ctx)
        return response, elapsed

    def _reply(self, response: Any, elapsed: float, text: str) -> LLMReply:
        text = text.strip()
        if not text:
            raise LLMError("Model returned an empty response.")
        reply = LLMReply(text=text, model=response.model,
                         prompt_tokens=response.prompt_eval_count,
                         output_tokens=response.eval_count,
                         seconds=round(elapsed, 1))
        log.info("LLM %s: %s in / %s out tokens, %.1fs", reply.model,
                 reply.prompt_tokens, reply.output_tokens, reply.seconds)
        return reply
