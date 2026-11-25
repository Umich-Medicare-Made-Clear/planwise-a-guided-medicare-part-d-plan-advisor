"""intake -> cost engine -> report input -> writer -> validator (code) -> reviewer (LLM) -> report.

Rejected drafts go back to the writer with feedback, up to max_attempts times.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents import ReportReviewerAgent, ReportWriterAgent
from src.engine import run_cost_engine
from src.llm import LLM, MODES, get_llm
from src.report_input import build_report_input
from src.validator import validate_report

log = logging.getLogger("planwise.pipeline")


@dataclass
class ReportOutcome:
    report: str
    approved: bool              # False -> a human should look before anyone sees it
    attempts: int
    problems: list[str] = field(default_factory=list)


def generate_report(
    report_input: dict[str, Any],
    *,
    llm: LLM | None = None,
    mode: str | None = None,
    max_attempts: int = 3,
    use_reviewer: bool = True,
) -> ReportOutcome:
    llm = llm or get_llm(mode)
    writer = ReportWriterAgent(llm)
    reviewer = ReportReviewerAgent(llm) if use_reviewer else None

    draft = writer.write(report_input).text
    problems: list[str] = []

    for attempt in range(1, max_attempts + 1):
        check = validate_report(draft, report_input)
        feedback = check.as_feedback()
        problems = check.errors + check.warnings

        # only spend an LLM review once the free checks pass
        if check.ok and reviewer is not None:
            verdict = reviewer.review(report_input, draft)
            problems += [f"[{i.severity}] {i.section}: {i.problem}" for i in verdict.issues]
            if verdict.passes:
                return ReportOutcome(draft, True, attempt, problems)
            feedback = "\n".join(filter(None, [feedback, verdict.as_feedback()]))
        elif check.ok:
            return ReportOutcome(draft, True, attempt, problems)

        log.info("Attempt %d rejected:\n%s", attempt, feedback)
        if attempt < max_attempts:
            draft = writer.revise(report_input, draft, feedback).text

    return ReportOutcome(draft, False, max_attempts, problems)


@dataclass
class PlanwiseResult:
    engine_result: dict[str, Any]
    report_input: dict[str, Any] | None = None   # plans[0] has the numbers the results page shows
    outcome: ReportOutcome | None = None
    errors: list[str] = field(default_factory=list)


def run_planwise(engine_intake: dict[str, Any], **report_kwargs: Any) -> PlanwiseResult:
    """Full run from a tier1/2/3 intake record (see src.intake.to_engine_intake)."""
    engine_result = run_cost_engine(engine_intake)
    if engine_result.get("status") != "completed":
        return PlanwiseResult(engine_result, errors=engine_result.get("errors", []))

    report_input = build_report_input(engine_intake, engine_result)
    if not report_input["plans"]:
        # never write a recommendation when no plan could be estimated
        return PlanwiseResult(engine_result, report_input,
                              errors=["No plan could be estimated for this profile."])
    return PlanwiseResult(engine_result, report_input,
                          generate_report(report_input, **report_kwargs))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a PlanWise report.")
    parser.add_argument("input", type=Path, help="Report-input JSON (or an intake record with --intake)")
    parser.add_argument("--intake", action="store_true",
                        help="Input is a tier1/2/3 intake record; run the cost engine first")
    parser.add_argument("--out", type=Path, help="Write the Markdown report here")
    parser.add_argument("--mode", choices=MODES,
                        help="dev = local Ollama, prod = Gemini (default: $PLANWISE_MODE or dev)")
    parser.add_argument("--no-review", action="store_true", help="Skip the LLM reviewer")
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    options = dict(mode=args.mode, max_attempts=args.attempts, use_reviewer=not args.no_review)
    if args.intake:
        result = run_planwise(data, **options)
        if result.outcome is None:
            print("No report:", *result.errors, sep="\n  - ", file=sys.stderr)
            return 1
        outcome = result.outcome
    else:
        outcome = generate_report(data, **options)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(outcome.report, encoding="utf-8")
    else:
        print(outcome.report)

    status = "APPROVED" if outcome.approved else "NEEDS HUMAN REVIEW"
    print(f"\n[{status}] after {outcome.attempts} attempt(s)", file=sys.stderr)
    for p in outcome.problems:
        print(f"  - {p}", file=sys.stderr)
    return 0 if outcome.approved else 1


if __name__ == "__main__":
    raise SystemExit(main())
