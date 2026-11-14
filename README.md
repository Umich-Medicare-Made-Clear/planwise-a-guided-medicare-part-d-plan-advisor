# Planwise

## CMS data review and connected intake

- [CMS Data Integration Review](CMS_Data_Integration_Review.ipynb): source documentation, schemas, quality checks, Michigan plan coverage, and example joins.
- [Connected Intake Notebook](PlanWise_Intake_CMS_Connected.ipynb): Taylor Whipple’s questionnaire and profile structure connected to medication and pharmacy records, with one adapted synthetic example and input-validation checks.

Both notebooks include saved outputs for review without running Python. The integration work covers 12 selected Michigan stand-alone Part D plans in the 2026 third-quarter CMS release. It demonstrates data linkage, not validated annual costs or recommendations. Missing payment-rule matches for some longer fills remain documented in the review.

## Running the notebooks

To rerun the notebooks, download [Planwise_Data_Integration_Handoff.zip](Planwise_Data_Integration_Handoff.zip?raw=true) and extract its `planwise_data` folder, which includes the supporting scripts, evidence, reference data, requirements, and prepared `data/planwise.duckdb` database. Follow that package’s README for environment setup, open the notebooks from the `planwise_data` folder, and select the configured Python environment.

The prepared database is included inside the handoff ZIP. The large original source archives and Python environment are not included. The original intake design is Taylor’s; the connected version preserves that structure and replaces placeholder selections with source-linked medication and pharmacy records.
