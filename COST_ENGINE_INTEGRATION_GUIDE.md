# Cost engine: team integration guide

Rechelle Transeth · November 22, 2026 · Input/output format · Version 1

The engine accepts a structured synthetic intake profile and returns cost estimates for the 12 selected Michigan plans. It does not produce a ranking. The files in `handoff/` give the team a concrete interface to build against.

## Files to use

- `cost_input.schema.json`: machine-readable requirements for supported inputs.
- `cost_output.schema.json`: machine-readable requirements for the returned results, plan statuses and available costs.
- `input_success.json` / `output_success.json`: two reviewed medications at 30 days; all 12 plans have estimates.
- `input_partial.json` / `output_partial.json`: the same medications at 60 days; some plans cannot be estimated. This is a completed comparison with gaps, not a failed run.
- `input_clarification.json` / `output_clarification.json`: an unknown strength; the input is rejected with an explanation and no plan estimates.
- `calculation_checks.json`: separately derived expected amounts and engine results.

Schemas describe supported structure. Passing a schema does not establish that a drug is enabled, pharmacy belongs to the directory, or database records are complete. The engine performs those additional checks. Additional metadata fields are permitted; consumers should rely on documented fields.

## Input fields

| Field | Required content | Meaning |
|---|---|---|
| `tier1.lives_in_michigan` | `"Yes"` | Confirmed scope; residence ZIP is not used to filter the statewide plan list. |
| `tier1.extra_help_status` | `"No"` | Subsidized estimates are outside this prototype. This is not an eligibility decision. |
| `tier1.medications` | List, including an empty list if no drugs | Each entry must describe a selected product. |
| Medication `medication_name`, `strength`, `dosage_form` | Exact catalog labels | Labels must match the selected record; do not invent missing values. |
| Medication `rxcui` | String | Standardized RxNorm medication identifier. |
| Medication `ndc` | 11-digit string | National Drug Code identifying the selected product; retain leading zeros. |
| Medication `quantity_per_fill` | Positive finite number | Units dispensed, not number of prescriptions. |
| Medication `days_supply` | 30, 60 or 90 | How long that quantity lasts. Different drugs can have different lengths. |
| Medication `assume_year_round_use` | `true` | Fixed full-year schedule beginning January 1. |
| `tier1.pharmacy_location` | Selected directory record | Required keys: `location_id`, `pharmacy_number`, `npi`, `location_name`, `zip_code`; all strings. `npi` means National Provider Identifier. Keep the original directory record rather than rebuilding its label. |
| `tier2`, `tier3` | Optional objects | Preferences passed through for explanation; they do not change costs or rank plans. |

The schema intentionally limits accepted scope. The clarification example passes structural checks but fails the catalog-label check. Only atorvastatin 20 mg product 60505257908 and lisinopril 10 mg product 68180098003 are enabled. Other products require review. Brand/generic substitutions are not automatic.

## Output fields and handling

| Field | Meaning and consumer action |
|---|---|
| Top-level `status` | `completed` means processing finished, not that every plan has an estimate. `invalid_or_unsupported_input` means read `errors`; `plans` is empty. |
| `plan_year`, `source_release`, `schedule`, `assumptions`, `validation` | Carry these into the combined summary input so limitations remain available. |
| `preferences` | Original `tier2` and `tier3` preferences. Medication and pharmacy input remains in the separate input profile. |
| `coverage_summary` | Counts considered, estimated and unavailable plans; `complete_comparison` is false if any plan lacks an estimate. Absent on rejected input. |
| Plan `contract_id`, `plan_id`, `segment_id` | Together identify the plan; use all three strings to join results. |
| `premium`, `deductible`, `annual_premium` | Monthly premium, plan deductible amount and 12 monthly premiums. The deductible amount is not necessarily what the person pays. |
| `annual_medication_cost`, `annual_total` | Member medication expense includes deductible payments. Annual total is annual premium plus medication expense. |
| `deductible_paid` | Portion of medication expense spent toward the deductible; never add it again. Available only for successful estimates. |
| `monthly_costs` | 12 records: `month`, `premium`, `medication_cost`, `total`. Full fills may make monthly amounts uneven. |
| `average_monthly_total`, `peak_monthly_total` | Annual total divided by 12 and highest scheduled month, respectively. Neither establishes budget fit. |
| `fill_ledger` | Per-purchase date, product, supply length, modeled gross price, deductible payment, remaining payment, member payment and deductible balance. |
| `medication_inputs` | Selected product and source-linked price/tier/payment inputs used in the calculation. `rule` and optional `pre_rule` contain type, amount, minimum and maximum. Type `1` means fixed copay; `2` means fractional coinsurance. |
| `pharmacy_status` | `preferred` or `standard` when determined. May be absent for empty medication lists or early failures. |
| `warnings`, `unavailable_reasons`, `issue_codes` | Preserve these in combined data. Codes include missing payment rule, missing/ambiguous drug price, pharmacy unavailable, coverage restriction, quantity limit, annual limit rules unresolved and requires review. |

All money is serialized as decimal strings; use decimal arithmetic when consuming it. `null` means unavailable, not zero. A genuine `"0.00"` is a calculated amount. Compare numbers numerically, never sort their text labels.

An unavailable plan has null annual medication expense and annual total. It may still have a known premium. Do not display that premium as the full annual cost. Successful-only fields may be absent. Restrictions that prevent estimation are reported in reasons; they are not an approval or an exception decision.

## How this connects to the summary

The summary can use the questionnaire responses alongside the cost engine’s results to explain plan costs in terms of the person’s medications, pharmacy and preferences. The example JSON files show how that information is organized.

The cost engine returns plan comparisons but does not choose or rank plans. We still need to agree on how plans will be selected for the summary.

The summary should use the calculated amounts and include relevant warnings. When a cost cannot be estimated, it should say so clearly. These are prototype estimates that still need independent validation. Extra Help eligibility and subsidized costs are outside the current scope.

## Running the examples

This update ZIP supplements the **Planwise_Cost_Engine_Handoff.zip** already in GitHub. It does not include the database or replace that runnable package.

1. Extract the original cost-engine handoff ZIP if you have not already done so.
2. Extract this update ZIP and merge its `planwise_data` contents into that same folder, replacing matching files. Keep the existing `data`, `scripts` and other folders.
3. Activate the Python environment used for the original package. From the merged `planwise_data` folder, install the updated requirements and run:

```sh
python -m pip install -r requirements.txt
python scripts/cost_engine.py --profile handoff/input_success.json --output handoff/my_results.json
python scripts/prepare_cost_handoff.py
```

The final command regenerates examples, validates their schemas, and runs the separately derived arithmetic checks. The project requirements include `jsonschema` for schema validation. No language-model API is required. The JSON examples can be read without running Python; reproducing the calculations requires the prepared database from the original package.
