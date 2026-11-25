from __future__ import annotations

from typing import Any

from src.agents.base import AgentError, BaseAgent
from src.llm import LLM
from src.skills import build_tools

FALLBACK_ANSWER = (
    "I'm not able to answer that one clearly. For free help, call "
    "1-800-MEDICARE or your local SHIP counselor."
)


class PlanExplainerAgent(BaseAgent):
    """Follow-up Q&A on a finished report. The model picks which skills to call."""

    prompt_name = "explainer"
    temperature = 0.2
    max_tool_rounds = 6

    def __init__(self, report_input: dict[str, Any], report_markdown: str,
                 llm: LLM | None = None) -> None:
        super().__init__(llm)
        self.system_prompt = f"{self.system_prompt}\n\n{report_markdown}"
        self.tools = build_tools(report_input)
        # only the visible Q&A is kept between questions, not the tool calls
        self.history: list[dict[str, Any]] = []

    def ask(self, question: str) -> str:
        messages = [*self.history, {"role": "user", "content": question}]
        try:
            reply = self.llm.chat_with_tools(
                self.system_prompt, messages, self.tools,
                max_rounds=self.max_tool_rounds, temperature=self.temperature,
            )
            answer = reply.text
        except AgentError:
            answer = FALLBACK_ANSWER

        self.history += [{"role": "user", "content": question},
                         {"role": "assistant", "content": answer}]
        return answer
