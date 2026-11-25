from __future__ import annotations

import re
from typing import Any

from src.agents.base import AgentResult, BaseAgent

_FENCE = re.compile(r"^```(?:markdown|md)?\s*\n(.*?)\n```\s*$", re.DOTALL)

REVISE_INSTRUCTIONS = (
    "A review found problems with this report. Fix every ERROR. "
    "Fix WARNINGS where you can without breaking a rule. Keep "
    "everything else the same. Return only the full corrected report.\n\n"
)


class ReportWriterAgent(BaseAgent):
    """Explains the cost engine's results. Never picks plans or computes costs."""

    prompt_name = "writer"
    temperature = 0.0

    def write(self, report_input: dict[str, Any]) -> AgentResult:
        return self._clean(self.run(report_input))

    def revise(self, report_input: dict[str, Any], draft: str, feedback: str) -> AgentResult:
        # previous draft goes back as the model's own turn so it edits instead of rewriting
        return self._clean(self.run(report_input, extra_messages=[
            {"role": "assistant", "content": draft},
            {"role": "user", "content": REVISE_INSTRUCTIONS + feedback},
        ]))

    @staticmethod
    def _clean(result: AgentResult) -> AgentResult:
        # small models like to wrap the report in a code fence or '---' lines
        text = result.text.strip()
        match = _FENCE.match(text)
        if match:
            text = match.group(1).strip()
        result.text = text.strip("-").strip()
        return result
