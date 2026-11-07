"""Synthetic tests for 05_quality_report.py. No IFLS microdata needed."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

spec = spec_from_file_location("quality_report", SCRIPT_DIR / "05_quality_report.py")
quality = module_from_spec(spec)
spec.loader.exec_module(quality)


def example_panel():
    return pd.DataFrame({
        "pidlink": ["p1", "p2", "p3", "p4"],
        "blt_2005": ["1", "0", pd.NA, "1"],
        "poor_ifls3": ["1", pd.NA, "0", "1"],
        "baseline_poor": ["True", "False", "False", "True"],
        "eligible_all_core": ["True", "False", "False", "False"],
        "observed_ifls5": ["True", "True", "False", "True"],
        "cesd_observed_items": ["10", "9", pd.NA, "10"],
    }).astype("string")


def test_variable_completeness_counts_missing_and_observed():
    report = quality.check_completeness(example_panel())
    blt = report.set_index("variable").loc["blt_2005"]

    assert blt["n_total"] == 4
    assert blt["n_observed"] == 3
    assert blt["n_missing"] == 1
    assert blt["missing_pct"] == 25
    assert blt["unique_values"] == 2
    assert report.iloc[0]["missing_pct"] >= report.iloc[-1]["missing_pct"]


def test_selection_counts_include_missing_without_reclassifying():
    report = quality.check_selection(example_panel())
    blt = report.loc[report["variable"] == "blt_2005"].set_index("value")

    assert blt.loc["1", "n"] == 2
    assert blt.loc["0", "n"] == 1
    assert blt.loc["<MISSING>", "n"] == 1
    assert not report["variable"].eq("pidlink").any()


def test_main_saves_only_aggregate_reports(monkeypatch, tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    example_panel().to_csv(private / "person_panel_full.csv", index=False)

    reports = {}
    monkeypatch.setattr(quality, "intermediate_dir", lambda: private)
    monkeypatch.setattr(
        quality,
        "save_report",
        lambda frame, name: reports.update({name: frame.copy()}),
    )

    quality.main()

    assert set(reports) == {
        "05_variable_completeness.csv",
        "05_selection_and_treatment_counts.csv",
    }
    assert "pidlink" not in reports["05_selection_and_treatment_counts.csv"]["variable"].values


def test_missing_panel_gives_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(quality, "intermediate_dir", lambda: tmp_path)
    with pytest.raises(FileNotFoundError, match="Panel file not found"):
        quality.main()
