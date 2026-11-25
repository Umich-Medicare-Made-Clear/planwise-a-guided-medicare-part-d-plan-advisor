"""Thin wrapper around the cost engine in planwise_data/ (owned by the data team)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ENGINE_DIR = Path(os.getenv("PLANWISE_ENGINE_DIR",
                            Path(__file__).resolve().parents[1] / "planwise_data"))


def _scripts():
    # the engine's scripts use flat imports (`from intake_data import ...`)
    scripts = str(ENGINE_DIR / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import cost_engine
    import intake_data
    return cost_engine, intake_data


def run_cost_engine(intake: dict[str, Any]) -> dict[str, Any]:
    cost_engine, _ = _scripts()
    result = cost_engine.compare_plans(intake)
    # round-trip so Decimals become the same strings the engine writes to disk
    return json.loads(json.dumps(result, default=cost_engine.json_default))


def intake_helpers():
    return _scripts()[1]
