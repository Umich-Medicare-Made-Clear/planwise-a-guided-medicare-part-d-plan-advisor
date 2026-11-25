from __future__ import annotations

import json
from typing import Any

from src.llm import LLM, LLMError, LLMReply, get_llm
from src.prompts import load_prompt

AgentError = LLMError
AgentResult = LLMReply


class BaseAgent:
    """Subclasses set prompt_name (a file in src/prompts/) and temperature."""

    prompt_name: str = ""
    temperature: float = 0.0

    def __init__(self, llm: LLM | None = None) -> None:
        if not self.prompt_name:
            raise TypeError(f"{type(self).__name__} must set prompt_name")
        self.llm = llm or get_llm()
        self.system_prompt = load_prompt(self.prompt_name)

    def build_user_message(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        # sort_keys so the same input always gives the same prompt
        return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)

    def run(self, payload: Any, *, extra_messages: list[dict[str, Any]] | None = None) -> LLMReply:
        messages = [{"role": "user", "content": self.build_user_message(payload)}]
        if extra_messages:
            messages.extend(extra_messages)
        return self.llm.chat(self.system_prompt, messages, temperature=self.temperature)
