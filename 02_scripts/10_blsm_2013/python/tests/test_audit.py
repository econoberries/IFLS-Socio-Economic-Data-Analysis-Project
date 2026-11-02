"""Synthetic tests. No restricted IFLS data needed."""
from pathlib import Path
import runpy
import sys

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[4]
CODE = ROOT / "02_scripts" / "10_blsm_2013" / "python"
sys.path.insert(0, str(CODE))
import audit_common as a


def test_codes_keys_and_years():
    assert a.code(3.0) == "3"
    assert a.code(" C ") == "C"
    assert a.code(pd.NA) == "(missing)"
    assert a.key(pd.Series(["00123", " 00124 ", None])).tolist()[:2] == ["00123", "00124"]
    yr = a.year(pd.Series([2013, 2014, 9999]))
    assert yr.iloc[0] == 2013
    assert yr.iloc[1] == 2014
    assert pd.isna(yr.iloc[2])
    tbl = a.labelled_codes(pd.Series([3, 3, 1]), {3: "BLSM", 1: "BLT"})
    assert dict(zip(tbl.code, tbl.n)) == {"3": 2, "1": 1}


def test_treatment_script_with_synthetic_stata(tmp_path, monkeypatch):
    path = tmp_path / "01_data" / "01_raw_dta" / "ifls5" / "household"
    path.mkdir(parents=True)
    data = pd.DataFrame({
        "hhid14": ["0001", "0002", "0003", "0004"],
        "ksr3type": [3, 3, 3, 1],
        "ksr17": [1, 3, 1, 1],
        "ksr18y": [2013, 2013, 2014, 2008],
        "ksr18m": [6, 6, 11, 11],
        "ksr22y": [2013, 2013, 2014, 2008],
        "ksr22m": [9, 9, 11, 11],
    })
    pyreadstat.write_dta(
        data, str(path / "b1_ksr1.dta"),
        variable_value_labels={
            "ksr3type": {1: "BLT", 3: "BLSM"},
            "ksr17": {1: "Yes", 3: "No"}
        }
    )
    monkeypatch.setattr(a, "ROOT", tmp_path)
    monkeypatch.setattr(a, "RAW", tmp_path / "01_data" / "01_raw_dta")
    monkeypatch.setattr(a, "OUTPUT", tmp_path / "05_outputs" / "tables" / "blsm_2013_python")
    runpy.run_path(str(CODE / "01_treatment_audit.py"), run_name="__main__")
    out = pd.read_csv(a.OUTPUT / "01_blsm_timing_categories.csv")
    counts = dict(zip(out.classification, out.n))
    assert counts["yes_first_2013"] == 1
    assert counts["reported_no"] == 1
    assert counts["yes_first_after_2013"] == 1
    # No household identifiers exported.
    for file in a.OUTPUT.glob("*.csv"):
        assert "hhid14" not in pd.read_csv(file).columns
