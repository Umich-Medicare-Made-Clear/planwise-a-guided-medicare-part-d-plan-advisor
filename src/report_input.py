"""Cost engine output -> the JSON the report agents read (see prompts/writer.md INPUT).

All arithmetic and ranking happens here, in code. The model only copies values.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

HELP_CONTACTS = [
    {"name": "1-800-MEDICARE", "phone": "1-800-633-4227",
     "note": "Open 24 hours a day, 7 days a week"},
    {"name": "MMAP (Michigan SHIP)", "phone": "1-800-803-7174",
     "note": "Free, unbiased Medicare counseling"},
]

UNAVAILABLE_REASONS = {
    "annual_limit_rules_unresolved": "Your yearly drug costs are high enough that we can't estimate them for this plan yet.",
    "missing_payment_rule": "The plan's payment rules for one of your medications at your fill length were not available.",
    "missing_or_ambiguous_drug_price": "A price for one of your medications at your fill length was not available.",
    "pharmacy_unavailable": "We could not confirm your pharmacy is in this plan's network.",
    "coverage_restriction": "One of your medications needs prior authorization or step therapy on this plan.",
    "quantity_limit": "Your quantity is more than this plan's quantity limit for one of your medications.",
    "requires_review": "This plan needs a manual review before we can estimate it.",
}


def money(value: Any) -> str:
    return f"${Decimal(str(value)):,.2f}"


def _number(value: Any) -> int | float:
    d = Decimal(str(value))
    return int(d) if d == d.to_integral_value() else float(d)


def _profile(intake: dict[str, Any]) -> dict[str, Any]:
    t1, t2, t3 = intake["tier1"], intake.get("tier2", {}), intake.get("tier3", {})
    ph = t1.get("pharmacy_location") or {}
    return {
        "state": "MI" if t1.get("lives_in_michigan") == "Yes" else "",
        "medications": [
            {"name": m["medication_name"], "strength": m.get("strength"),
             "form": m.get("dosage_form"), "quantity_per_fill": _number(m["quantity_per_fill"]),
             "days_supply": m["days_supply"]}
            for m in t1.get("medications") or []
        ],
        "pharmacy": {
            "name": ph.get("organization_name"),
            "address": f"{ph.get('address')}, {ph.get('city')}, {ph.get('state')} {ph.get('zip_code')}",
        },
        "open_to_other_pharmacy": t2.get("consider_another_retail_pharmacy", "Not sure"),
        "report_focus": t3.get("explanation_focus", "Balanced overview"),
        "extra_help": t1.get("extra_help_status", "No"),
    }


def _medications(plan: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for med in plan.get("medication_inputs") or []:
        ndc = med["ndc"]
        payments = sorted({Decimal(str(r["member_payment"]))
                           for r in plan["fill_ledger"] if r["ndc"] == ndc})
        # what they pay per fill changes once the deductible is met
        per_fill = (money(payments[0]) if len(payments) == 1
                    else f"{money(payments[0])} to {money(payments[-1])}")
        restrictions = ["quantity limit"] if any(
            "Quantity limit" in w and ndc in w for w in plan.get("warnings", [])) else []
        out.append({
            "name": med["medication_name"],
            "covered": True,
            "tier": med["tier"],
            "cost_per_fill": per_fill,
            "deductible_applies": med["deductible_applies"],
            "restrictions": restrictions,
        })
    # not-covered/restricted drugs first, as the report table expects
    return sorted(out, key=lambda m: not m["restrictions"])


def _plan(plan: dict[str, Any]) -> dict[str, Any]:
    out = {
        "plan_name": plan["plan_name"],
        "monthly_premium": money(plan["premium"]),
        "annual_premium": money(plan["annual_premium"]),
        "annual_deductible": money(plan["deductible"]),
        "estimated_annual_drug_cost": money(plan["annual_medication_cost"]),
        "estimated_total_annual_cost": money(plan["annual_total"]),
        "medications": _medications(plan),
        "monthly_cost_schedule": [
            {"month": calendar.month_name[m["month"]], "total": money(m["total"])}
            for m in plan.get("monthly_costs") or []
        ],
        "predictability_metric": {
            "highest_month_total": money(plan["peak_monthly_total"]),
            "average_month_total": money(plan["average_monthly_total"]),
        },
    }
    # the engine only checks the network when there are medications to price
    if plan.get("pharmacy_status"):
        out["pharmacy_network_status"] = plan["pharmacy_status"]
    return out


def rank_plans(engine_result: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Estimated plans sorted by yearly total; unavailable plans are never ranked as $0."""
    plans = engine_result.get("plans") or []
    estimated = [p for p in plans if p.get("annual_total") is not None]
    unavailable = [p for p in plans if p.get("annual_total") is None]
    estimated.sort(key=lambda p: (Decimal(str(p["annual_total"])),
                                  Decimal(str(p["premium"])), p["plan_name"]))
    return estimated, unavailable


def build_report_input(intake: dict[str, Any], engine_result: dict[str, Any], *,
                       report_date: date | None = None,
                       enrollment_deadline: str | None = None) -> dict[str, Any]:
    if engine_result.get("status") != "completed":
        raise ValueError(f"Cost engine did not complete: {engine_result.get('errors')}")
    estimated, unavailable = rank_plans(engine_result)

    meta = {
        "plan_year": engine_result.get("plan_year"),
        "data_as_of": f"{engine_result.get('source_release')} CMS data",
        "report_date": (report_date or date.today()).isoformat(),
        "help_contacts": HELP_CONTACTS,
    }
    if enrollment_deadline:
        meta["enrollment_deadline"] = enrollment_deadline

    return {
        "meta": meta,
        "profile": _profile(intake),
        "plans": [{"rank": i, **_plan(p)} for i, p in enumerate(estimated, 1)],
        "plans_without_estimate": [
            {"plan_name": p["plan_name"],
             "reason": UNAVAILABLE_REASONS.get(
                 (p.get("issue_codes") or ["requires_review"])[0],
                 UNAVAILABLE_REASONS["requires_review"])}
            for p in unavailable
        ],
    }
