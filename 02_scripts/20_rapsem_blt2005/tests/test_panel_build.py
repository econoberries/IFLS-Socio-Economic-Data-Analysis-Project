"""Synthetic tests for 04_build_panel.py. No IFLS microdata are needed."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

spec = spec_from_file_location("panel_builder", SCRIPT_DIR / "04_build_panel.py")
panel_builder = module_from_spec(spec)
spec.loader.exec_module(panel_builder)


def test_roster_filters_former_members(monkeypatch):
    source = pd.DataFrame({
        "pidlink": ["p1", "p2", "p3"],
        "hhid00": ["h1", "h1", "h1"],
        "ar01a": [1, 5, 3],
        "ar09": [40, 25, 50],
    })
    monkeypatch.setattr(panel_builder, "stata", lambda wave, file: (source, None))

    settings = {
        "approved": True,
        "file": "bk_ar1",
        "pid": "pidlink",
        "household": "hhid00",
        "membership": "ar01a",
        "age": "ar09",
        "current_codes": [1, 5],
    }
    result = panel_builder.load_roster("ifls3", settings)
    assert result["pidlink"].tolist() == ["p1", "p2"]
    assert len(result) == 2


def test_load_blt_preserves_unknown_as_missing(monkeypatch):
    source = pd.DataFrame({
        "hhid07": ["h1", "h2", "h3"],
        "blt_2005_06_candidate": ["1", "0", pd.NA],
    })
    monkeypatch.setattr(
        panel_builder, "read_local_csv", lambda filename: source.copy()
    )
    result = panel_builder.load_blt().set_index("hhid_ifls4")
    assert result.loc["h1", "blt_2005"] == 1
    assert result.loc["h2", "blt_2005"] == 0
    assert pd.isna(result.loc["h3", "blt_2005"])


def test_load_blt_rejects_duplicate_households(monkeypatch):
    source = pd.DataFrame({
        "hhid07": ["h1", "h1"],
        "blt_2005_06_candidate": ["1", "0"],
    })
    monkeypatch.setattr(
        panel_builder, "read_local_csv", lambda filename: source.copy()
    )
    with pytest.raises(ValueError, match="unique"):
        panel_builder.load_blt()


def test_load_cesd_recounts_valid_items(monkeypatch):
    items = [f"cesd_{letter}" for letter in "ABCDEFGHIJ"]
    source = pd.DataFrame({
        "pidlink": ["p1", "p2"],
        **{item: [0, 3] for item in items},
    })
    source.loc[1, "cesd_C"] = pd.NA
    monkeypatch.setattr(
        panel_builder, "read_local_csv", lambda filename: source.copy()
    )
    result = panel_builder.load_cesd().set_index("pidlink")
    assert result.loc["p1", "cesd_observed_items"] == 10
    assert result.loc["p2", "cesd_observed_items"] == 9
    assert not result.loc["p2", "cesd_complete_10"]


def test_load_welfare_zero_is_not_a_finite_log(monkeypatch):
    source = pd.DataFrame({
        "wave": ["ifls3", "ifls5"],
        "hhid": ["h1", "h2"],
        "monthly_pce": ["0", "500"],
        "monthly_poverty_line": ["400", "400"],
    })
    monkeypatch.setattr(
        panel_builder, "read_local_csv", lambda filename: source.copy()
    )
    settings = {
        "file": "ignored",
        "wave_column": "wave",
        "household_column": "hhid",
        "pce_column": "monthly_pce",
        "poverty_line_column": "monthly_poverty_line",
    }
    result = panel_builder.load_welfare(settings)
    assert pd.isna(result.loc[0, "log_pce_pl"])
    assert pd.isna(result.loc[0, "poor"])
    assert result.loc[1, "poor"] == 0


def test_full_panel_keeps_baseline_people_and_missing_followup(monkeypatch, tmp_path):

    settings = {"approved": True}
    config = {
        "rosters": {wave: settings for wave in ["ifls3", "ifls4", "ifls5"]},
        "treatment": {
            "approved": True,
            "exposure_assignment_verified": True,
        },
        "mediator": {"approved": True},
        "welfare": {
            "approved": True,
            "file": "ignored",
        },
        "analysis": {"minimum_age_ifls3": 18, "baseline_poor_only": True},
        "baseline_covariates": [],
    }

    def roster(wave, config):
        if wave == "ifls3":
            return pd.DataFrame({
                "pidlink": ["p1", "p2", "p3"],
                "hhid_ifls3": ["h0", "h0", "h3"],
                "age_ifls3": [35, 24, 16],
            })
        if wave == "ifls4":
            return pd.DataFrame({
                "pidlink": ["p1", "p2"],
                "hhid_ifls4": ["h4", "h4"],
                "age_ifls4": [42, 31],
            })
        return pd.DataFrame({
            "pidlink": ["p1"],
            "hhid_ifls5": ["h5"],
            "age_ifls5": [49],
        })

    def welfare(config):
        return pd.DataFrame({
            "wave": ["ifls3", "ifls5"],
            "hhid": ["h0", "h5"],
            "monthly_pce": [300.0, 600.0],
            "poverty_line": [400.0, 500.0],
            "log_pce_pl": [-0.287682, 0.182321],
            "poor": pd.array([1, 0], dtype="Int64"),
        })

    items = [f"cesd_{letter}" for letter in "ABCDEFGHIJ"]
    cesd = pd.DataFrame({
        "pidlink": ["p1", "p2"],
        **{item: [0, 1] for item in items},
        "cesd_observed_items": [10, 10],
        "cesd_complete_10": [True, True],
    })

    monkeypatch.setattr(panel_builder, "read_config", lambda: config)
    monkeypatch.setattr(panel_builder, "load_roster", roster)
    monkeypatch.setattr(panel_builder, "load_blt", lambda: pd.DataFrame({
        "hhid_ifls4": ["h4"], "blt_2005": pd.array([1], dtype="Int64"),
    }))
    monkeypatch.setattr(panel_builder, "load_cesd", lambda: cesd)
    monkeypatch.setattr(panel_builder, "load_welfare", welfare)

    private = tmp_path / "private"
    analysis = tmp_path / "analysis"
    private.mkdir()
    analysis.mkdir()
    monkeypatch.setattr(panel_builder, "intermediate_dir", lambda: private)
    monkeypatch.setattr(panel_builder, "analysis_dir", lambda: analysis)
    monkeypatch.setattr(
        panel_builder,
        "save_private",
        lambda data, name: data.to_csv(private / name, index=False),
    )
    reports = []
    monkeypatch.setattr(
        panel_builder,
        "save_report",
        lambda data, name: reports.append((name, data.copy())),
    )

    panel_builder.main()

    result = pd.read_csv(private / "person_panel_full.csv").set_index("pidlink")
    assert len(result) == 2  # age-16 person was excluded from baseline
    assert result.loc["p1", "poverty_exit_2014"] == 1
    assert pd.isna(result.loc["p2", "poor_ifls5"])
    assert result["blt_2005"].eq(1).all()  # same IFLS4 household
    assert result["eligible_all_core"].sum() == 1
    assert len(pd.read_csv(analysis / "baseline_poor_analysis_panel.csv")) == 2
    assert reports[0][0] == "04_panel_sample_flow.csv"
