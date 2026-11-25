"""Streamlit intake (utils/intake_data.collect_intake_data) -> cost engine tier1/2/3 record."""
from __future__ import annotations

from typing import Any

from src.engine import intake_helpers

NO_ASSISTANCE = "I don't receive any of these"

FOCUS_BY_COST_PREFERENCE = {
    "The lowest estimated total annual cost": "Estimated annual total",
    "More predictable costs throughout the year": "Why costs may vary during the year",
    "A balance between cost and predictability": "Balanced overview",
    "I'm not sure": "Balanced overview",
}


class IntakeError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def _yes_no_unsure(answer: str) -> str:
    return "Not sure" if answer == "I'm not sure" else answer


def _days(value: Any) -> int | None:
    # the app stores "30 days" / "Other"
    head = str(value).split()[0] if value else ""
    return int(head) if head.isdigit() else None


def to_engine_intake(app: dict[str, Any]) -> dict[str, Any]:
    helpers = intake_helpers()
    problems: list[str] = []

    meds = []
    if not app.get("no_medications"):
        for i, med in enumerate(app.get("medications") or [], 1):
            label = med.get("name") or f"Medication {i}"
            days = _days(med.get("days_supply"))
            if days not in (30, 60, 90):
                problems.append(f"{label}: only 30, 60 or 90 day fills can be priced.")
                continue
            # The engine needs a catalog product, not free text. The app must let the
            # person pick one (src/engine -> lookup.match_medication) and store its rxcui/ndc.
            if not med.get("rxcui"):
                problems.append(f"{label}: pick the exact product from the catalog.")
                continue
            try:
                meds.append(helpers.select_medication(
                    med["rxcui"], med.get("quantity"), days, med.get("ndc")))
            except ValueError as exc:
                problems.append(f"{label}: {exc}")

    pharmacy = None
    number = app.get("pharmacy_number")
    if not number:
        problems.append("Pick a specific pharmacy location; the engine can't price without one.")
    else:
        _, directory = helpers.load_catalogs()
        pharmacy = next((p for p in directory if p["pharmacy_number"] == number), None)
        if pharmacy is None:
            problems.append("That pharmacy isn't in the Michigan pharmacy directory.")

    if problems:
        raise IntakeError(problems)

    return {
        "tier1": {
            "lives_in_michigan": app.get("lives_in_michigan", ""),
            "zip_code": app.get("zip_code", ""),
            "medications": meds,
            "pharmacy_location": pharmacy,
            # Medicaid, SSI and MSP all come with Extra Help, which the engine can't price yet
            "extra_help_status": "No" if app.get("assistance") == NO_ASSISTANCE else "Yes",
            "first_time_part_d": _yes_no_unsure(app.get("part_d_experience", "")),
        },
        "tier2": {
            "consider_another_retail_pharmacy": _yes_no_unsure(app.get("switch_pharmacy", "")),
        },
        "tier3": {
            "explanation_focus": FOCUS_BY_COST_PREFERENCE.get(
                app.get("cost_preference", ""), "Balanced overview"),
        },
    }
