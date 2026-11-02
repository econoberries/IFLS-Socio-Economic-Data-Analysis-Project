"""Shared, read-only utilities for the IFLS BLSM 2013 Python audit.

Run scripts from the directory containing IFLS_Project.Rproj.
Original .dta files and all person/household identifiers stay local.
"""
from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

ROOT = Path.cwd()
if not (ROOT / "IFLS_Project.Rproj").is_file():
    raise RuntimeError("Open the IFLS RStudio project root before running this script.")

RAW = ROOT / "01_data" / "01_raw_dta"
OUTPUT = ROOT / "05_outputs" / "tables" / "blsm_2013_python"


def find_dta(wave: str, stem: str, required: bool = True) -> Path | None:
    folder = RAW / wave
    hits = sorted(p for p in folder.rglob("*") if p.is_file()
                  and p.suffix.lower() == ".dta" and p.stem.lower() == stem.lower()
                  ) if folder.is_dir() else []
    if not hits and not required:
        return None
    if len(hits) != 1:
        raise FileNotFoundError(f"Expected exactly one {stem}.dta in {folder}; found: {hits}")
    return hits[0]


def read_stata(wave: str, stem: str, metadata_only: bool = False):
    """Preserve raw codes and Stata metadata; don't apply value formats."""
    try:
        import pyreadstat
    except ImportError as error:
        raise RuntimeError("Install: python -m pip install -r 02_scripts/10_blsm_2013/python/requirements.txt") from error
    df, meta = pyreadstat.read_dta(
        str(find_dta(wave, stem)),
        apply_value_formats=False,
        user_missing=True,
        metadataonly=metadata_only,
    )
    return df, meta


def code(value) -> str:
    if pd.isna(value):
        return "(missing)"
    if isinstance(value, str):
        return value.strip()
    try:
        if float(value).is_integer():
            return str(int(float(value)))
    except (TypeError, ValueError, OverflowError):
        pass
    return str(value)


def labelled_codes(series: pd.Series, mapping: dict | None = None) -> pd.DataFrame:
    """Aggregate codes and original Stata value labels; no microdata exported."""
    mapping = mapping or {}
    values = series.map(code)
    labels = {code(k): str(v) for k, v in mapping.items()}
    table = values.value_counts(dropna=False).rename_axis("code").reset_index(name="n")
    table["label"] = table["code"].map(labels).fillna("(unlabelled)")
    return table[["code", "label", "n"]]


def variable_dictionary(meta, wave: str, file: str) -> pd.DataFrame:
    names = list(meta.column_names)
    labels = meta.column_names_to_labels or {}
    return pd.DataFrame({
        "wave": wave, "file": file, "variable": names,
        "description": [labels.get(name) or "" for name in names]
    })


def save_aggregate(table: pd.DataFrame, name: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    table.to_csv(path, index=False)
    print(f"Saved {path.relative_to(ROOT)} ({len(table)} rows)")


def key(series: pd.Series) -> pd.Series:
    """Keep identifiers as strings, never turn into integers."""
    values = series.astype("string").str.strip()
    return values.mask(values.eq(""))


def year(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values.between(2000, 2015)).astype("Int64")


def check_columns(df: pd.DataFrame, cols: list[str], source: str) -> None:
    absent = sorted(set(cols) - set(df.columns))
    if absent:
        raise ValueError(f"{source}: missing {absent}. Inspect the saved variable dictionary.")
