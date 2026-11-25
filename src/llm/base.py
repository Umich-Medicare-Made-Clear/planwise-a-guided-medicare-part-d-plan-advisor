from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class LLMError(RuntimeError):
    pass


@dataclass
class LLMReply:
    text: str
    model: str
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    seconds: float = 0.0
    tool_calls_made: list[str] = field(default_factory=list)


class LLM(Protocol):
    model: str

    def chat(self, system: str, messages: list[dict[str, Any]], *,
             json_schema: dict[str, Any] | None = None,
             temperature: float = 0.0) -> LLMReply: ...

    def chat_with_tools(self, system: str, messages: list[dict[str, Any]],
                        tools: list[Callable[..., str]], *, max_rounds: int = 6,
                        temperature: float = 0.0) -> LLMReply: ...


def parse_json(text: str) -> Any:
    # some models wrap JSON in a ```json fence even when asked not to
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(cleaned)


def run_tool(by_name: dict[str, Callable[..., str]], name: str, args: dict[str, Any]) -> str:
    fn = by_name.get(name)
    if fn is None:
        return f"Error: no tool named {name!r}."
    try:
        return str(fn(**args))
    except Exception as exc:
        # hand the error back to the model instead of crashing the conversation
        return f"Error running {name}: {exc}"
