"""Synthetic tests: no IFLS microdata required. Run with pytest."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))


def load_script(alias, filename):
    spec = spec_from_file_location(alias, SCRIPT_DIR / filename)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


blt = load_script("candidate_blt", "03a_build_blt_treatment.py")
cesd = load_script("candidate_cesd", "03b_build_cesd_indicators.py")


def blt_fixture():
    return pd.DataFrame({
        "hhid07": ["h1", "h2", "h3", "h4", "h5", "b1"],
        "ksr3type": ["A", "A", "A", "A", "A", "B"],
        "ksr17": [1, 3, 1, 1, 9, 1],
        "ksr18y": [2005, None, 2007, 9998, None, 2005],
        "ksr22y": [2006, None, 2008, 9999, None, 2006],
    })


def cesd_fixture():
    rows = []
    for pid, screen, frequency in [
        ("p1", 3, None),
        ("p2", 1, 4),
    ]:
        for item in "ABCDEFGHIJ":
            rows.append({
                "pidlink": pid,
                "kptype": item,
                "kp01": screen,
                "kp02": frequency,
            })
    return pd.DataFrame(rows)


def test_blt_respects_program_and_ambiguous_years():
    output = blt.classify_blt(blt_fixture()).set_index("hhid07")
    assert len(output) == 5
    assert output.loc["h1", "blt_2005_06_candidate"] == 1
    assert output.loc["h2", "blt_2005_06_candidate"] == 0
    assert output.loc["h3":"h5", "blt_2005_06_candidate"].isna().all()


def test_blt_rejects_repeated_program_households():
    data = blt_fixture()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        blt.classify_blt(data)


def test_cesd_skips_and_reversed_positive_items():
    _, wide = cesd.build_cesd(cesd_fixture())
    wide = wide.set_index("pidlink")
    assert len(wide) == 2
    assert wide.loc["p1", "cesd_A"] == 0
    assert wide.loc["p1", "cesd_E"] == 3
    assert wide.loc["p1", "cesd_H"] == 3
    assert wide.loc["p2", "cesd_A"] == 3
    assert wide.loc["p2", "cesd_E"] == 0
    assert wide["cesd_valid_items"].eq(10).all()


def test_cesd_unverified_code_is_missing_not_zero():
    data = cesd_fixture()
    data.loc[(data.pidlink == "p1") & (data.kptype == "C"), "kp01"] = 9
    _, wide = cesd.build_cesd(data)
    wide = wide.set_index("pidlink")
    assert pd.isna(wide.loc["p1", "cesd_C"])
    assert wide.loc["p1", "cesd_valid_items"] == 9


def test_cesd_rejects_duplicate_item():
    data = cesd_fixture()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        cesd.build_cesd(data)
