# Planwise cost engine handoff

Download and extract `Planwise_Cost_Engine_Handoff.zip` into a new folder. It contains a self-contained `planwise_data` directory with the prepared CMS database, calculator, intake helpers, tests, saved results and reference metadata. The earlier data-integration ZIP is not needed to run this package.

## Review

Open `Planwise_Cost_Engine.ipynb` on GitHub to read saved outputs, or download `Planwise_Cost_Engine.html` and open it in a browser.

## Run

Use Python 3.12. From the extracted `planwise_data` directory:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/cost_engine.py
python scripts/development_profiles.py
python -m unittest discover -s tests -p test_cost_engine.py
```

On Windows, activate with `.venv\Scripts\activate` instead. In VS Code, select this environment as the notebook kernel and run the notebook from the extracted folder.

## Connect intake profiles

Use `evidence/integrated_intake_example.json` for the expected structure. Run `python scripts/cost_engine.py --profile path/to/profile.json --output path/to/results.json`. The output directory must already exist. `compare_profiles` in `scripts/cost_engine.py` also accepts a dictionary of profile names and intake records. Profiles must be synthetic.

An unavailable estimate has a null annual total and an explanation; it must not be treated as zero. The engine currently enables only the two reviewed medication products, accepts 30/60/90-day retail fills, excludes Extra Help, and blocks higher spending that requires unresolved annual coverage rules. See `docs/COST_ENGINE.md` for assumptions and limitations. The 29 internal checks are not independent validation against Plan Finder.
