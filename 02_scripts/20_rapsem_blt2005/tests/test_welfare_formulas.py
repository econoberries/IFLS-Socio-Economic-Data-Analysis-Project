"""Synthetic tests for the beginner-friendly welfare builder; no IFLS data needed."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))


def load_welfare():
    spec = spec_from_file_location("welfare_builder", SCRIPT_DIR / "03_build_welfare.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


welfare = load_welfare()


def test_household_size_uses_only_approved_roster_members(monkeypatch):
    roster = pd.DataFrame({
        "pidlink": ["p1", "p2", "p3", "p4"],
        "hhid00": ["h1", "h1", "h1", "h2"],
        "ar01a": [1, 5, 3, 1],
    })
    monkeypatch.setattr(welfare, "stata", lambda wave, file: (roster.copy(), None))
    settings = {
        "approved": True, "file": "bk_ar1",
        "pid": "pidlink", "household": "hhid00",
        "membership": "ar01a", "current_codes": [1, 5],
    }

    sizes = welfare.get_household_size("ifls3", settings).set_index("hhid")
    assert sizes.loc["h1", "household_size"] == 2
    assert sizes.loc["h2", "household_size"] == 1


def test_monthly_component_does_not_turn_missing_into_zero(monkeypatch):
    source = pd.DataFrame({
        "hhid00": ["h1", "h1", "h2"],
        "ks1type": ["A", "B", "A"],
        "purchase": [100, 200, 9999],
        "own_production": [10, 0, 5],
    })
    monkeypatch.setattr(welfare, "stata", lambda wave, file: (source.copy(), None))
    settings = {
        "file": "b1_ks1", "household": "hhid00",
        "item_column": "ks1type", "include_codes": ["A", "B"],
        "all_rows_approved": False,
        "amount_columns": ["purchase", "own_production"],
        "multiply_to_monthly": 4,
    }

    amount, name, audit = welfare.get_expenditure(
        "ifls3", settings, 1, missing_codes=[9999]
    )
    amount = amount.set_index("hhid")

    assert amount.loc["h1", name] == 1240
    assert pd.isna(amount.loc["h2", name])
    assert amount.loc["h2", f"{name}_missing"] == 1
    assert audit["total_missing_item_values"] == 1


def test_approved_missing_as_zero_only_for_named_column(monkeypatch):
    source = pd.DataFrame({
        "hhid14": ["h1"],
        "ks1type": ["A"],
        "purchase": [100],
        "own_production": [np.nan],
    })
    monkeypatch.setattr(welfare, "stata", lambda wave, file: (source.copy(), None))
    settings = {
        "file": "b1_ks1", "household": "hhid14",
        "all_rows_approved": True,
        "amount_columns": ["purchase", "own_production"],
        "zero_if_missing_columns": ["own_production"],
        "multiply_to_monthly": 1,
    }

    amount, name, _ = welfare.get_expenditure("ifls5", settings, 1, [])
    assert amount.loc[0, name] == 100


def test_poverty_log_and_zero_welfare_rule():
    frame = pd.DataFrame({
        "monthly_pce": [400.0, 500.0, 600.0, 0.0, 500.0],
        "monthly_poverty_line": [500.0, 500.0, 500.0, 500.0, np.nan],
    })
    result = welfare.calculate_poverty(frame)
    assert result["poor"].tolist()[:3] == [1, 0, 0]
    assert result.loc[0, "log_pce_pl"] == pytest.approx(np.log(0.8))
    assert pd.isna(result.loc[3, "log_pce_pl"])
    assert pd.isna(result.loc[3, "poor"])
    assert pd.isna(result.loc[4, "poor"])
