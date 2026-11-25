from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from src.agents.base import AgentError, BaseAgent
from src.llm import parse_json
from src.prompts import load_prompt


class ReviewIssue(BaseModel):
    section: str = Field(description="Report section heading the issue is in")
    problem: str = Field(description="One sentence describing what is wrong")
    fix: str = Field(description="Concrete change the writer should make")
    severity: Literal["blocker", "minor"]


class ReviewVerdict(BaseModel):
    passes: bool = Field(description="True only if there are no blocker issues")
    reading_level_ok: bool
    issues: list[ReviewIssue]

    def as_feedback(self) -> str:
        return "\n".join(
            f"- {'ERROR' if i.severity == 'blocker' else 'WARNING'} "
            f"[{i.section}]: {i.problem} Fix: {i.fix}"
            for i in self.issues
        )


class ReportReviewerAgent(BaseAgent):
    """LLM-as-judge for the things the regex validator can't check."""

    prompt_name = "reviewer"
    temperature = 0.0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # judge against the same rules the writer was given
        self.system_prompt = f"{self.system_prompt}\n\n{load_prompt('writer')}"

    def review(self, report_input: dict[str, Any], draft: str) -> ReviewVerdict:
        input_json = json.dumps(report_input, indent=2, sort_keys=True, ensure_ascii=False)
        user = (
            f"<report_input>\n{input_json}\n</report_input>\n\n"
            f"<draft_report>\n{draft}\n</draft_report>\n\n"
            "Return your review as JSON."
        )
        reply = self.llm.chat(
            self.system_prompt,
            [{"role": "user", "content": user}],
            json_schema=ReviewVerdict.model_json_schema(),
            temperature=self.temperature,
        )
        try:
            verdict = ReviewVerdict.model_validate(parse_json(reply.text))
        except (ValueError, ValidationError) as exc:
            raise AgentError(f"Reviewer returned invalid JSON: {exc}") from exc
        # trust the issue list, not the model's own pass/fail flag
        verdict.passes = not any(i.severity == "blocker" for i in verdict.issues)
        return verdict
