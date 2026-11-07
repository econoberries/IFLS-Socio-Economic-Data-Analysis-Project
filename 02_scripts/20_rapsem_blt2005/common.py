"""
common.py

Shared functions for our IFLS causal inference project.

This file helps other scripts:
1. Locate the IFLS project and folders.
2. Find and read original Stata datasets.
3. Standardize identifiers and variable codes.
4. Check required columns and duplicate IDs.
5. Load configuration files.
6. Save audit reports and private datasets.

Original IFLS .dta files are never modified.
"""

import json
from pathlib import Path

import pandas as pd


# ============================================================
# 1. PROJECT SETTINGS
# ============================================================

STUDY = "rapsem_blt2005"

REQUIRED = ["ifls3", "ifls4", "ifls5"]

# Candidate datasets used in our initial IFLS audits
STEMS = {
    "ifls3": [
        "bk_ar1", "bk_ar0", "bk_krk",
        "b1_ks0", "b1_ks1", "b1_ks2", "b1_ks3",
        "b2_kr", "b2_hr", "b2_ut", "b2_nt",
        "b3a_dl", "b3a_tk", "b3b_kk", "b3b_ma",
    ],
    "ifls4": [
        "bk_ar1", "bk_ar0", "bk_krk",
        "b1_ks0", "b1_ks1", "b1_ks2", "b1_ks3",
        "b1_ksr1", "b1_ksr3", "b1_ksr4",
        "b2_kr", "b2_hr",
        "b3a_dl", "b3a_tk", "b3b_kp", "ptrack",
    ],
    "ifls5": [
        "bk_ar1", "bk_ar0", "bk_krk",
        "b1_ks0", "b1_ks1", "b1_ks2", "b1_ks3",
        "b1_ksr1", "b2_kr", "b2_hr",
        "b3a_dl", "b3a_tk", "b3b_kp", "ptrack",
    ],
}


# ============================================================
# 2. DEFINE PROJECT FOLDERS
# ============================================================

def project_root():

    # Start from the current working directory.
    current_folder = Path.cwd().resolve()

    # Search upward for the existing IFLS project.
    for folder in [current_folder, *current_folder.parents]:

        has_project_file = (
            folder / "IFLS_Project.Rproj"
        ).is_file()

        has_data_folder = (
            folder / "01_data"
        ).is_dir()

        if has_project_file and has_data_folder:
            return folder

    raise SystemExit(
        "Project folder not found. "
        "Run from inside the folder containing IFLS_Project.Rproj."
    )


def script_dir():
    return Path(__file__).resolve().parent


def source_root():
    return project_root() / "01_data" / "01_raw_dta"


def output_dir():

    folder = project_root() / "05_outputs" / "tables" / STUDY
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def intermediate_dir():

    folder = project_root() / "01_data" / "04_intermediate" / STUDY
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def analysis_dir():

    folder = project_root() / "01_data" / "05_analysis" / STUDY
    folder.mkdir(parents=True, exist_ok=True)

    return folder


# ============================================================
# 3. FIND AND READ STATA DATASETS
# ============================================================

def find_dta(wave, stem, required=True):

    folder = source_root() / wave
    matches = []

    # Search subfolders for the requested Stata file.
    if folder.exists():

        for file in folder.rglob("*"):

            is_stata = file.suffix.lower() == ".dta"
            correct_name = file.stem.lower() == stem.lower()

            if file.is_file() and is_stata and correct_name:
                matches.append(file)

    matches = sorted(matches)

    # Do not choose arbitrarily between duplicate extractions.
    if len(matches) > 1:
        raise ValueError(
            f"Multiple copies of {stem}.dta found in {wave}. "
            "Check the raw data folders."
        )

    if not matches:

        if required:
            raise FileNotFoundError(
                f"Cannot find {stem}.dta in {folder}"
            )

        return None

    return matches[0]


def stata(wave, stem, metadataonly=False, usecols=None):

    import pyreadstat

    file_path = find_dta(wave, stem)

    # Keep original Stata codes, without applying value labels.
    options = {
        "apply_value_formats": False,
        "user_missing": True,
        "metadataonly": metadataonly,
    }

    if usecols is not None and not metadataonly:
        options["usecols"] = list(usecols)

    data, metadata = pyreadstat.read_dta(
        str(file_path),
        **options
    )

    return data, metadata


# ============================================================
# 4. STANDARDIZE VALUES
# ============================================================

def txt(value):

    # Keep missing values missing.
    if pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()
        return value or None

    # Convert 1.0 to "1" so numeric and string codes can be compared.
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return str(int(value))

    return str(value).strip() or None


def normalized(series):

    return series.map(txt).astype("string")


# ============================================================
# 5. VALIDATE DATA
# ============================================================

def require_columns(data, columns, context):

    missing = [
        column
        for column in columns
        if not column or column not in data.columns
    ]

    if missing:
        raise ValueError(
            f"{context}: Missing columns {missing}. "
            "Check the variable dictionary and codebook."
        )


def assert_unique(data, column, context):

    if data[column].isna().any():
        raise ValueError(
            f"{context}: {column} must be nonmissing and unique. "
            "Some IDs are missing."
        )

    if data[column].duplicated().any():
        raise ValueError(
            f"{context}: {column} must be unique. "
            "Duplicate IDs were found."
        )


# ============================================================
# 6. LOAD CONFIGURATION
# ============================================================

def read_config():

    config_path = script_dir() / "study_config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            "Missing study_config.json. "
            "Copy the example file and verify its settings."
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    return config


def approved(settings):

    if not settings.get("approved", False):
        raise ValueError(
            "Configuration not approved. "
            "Check variables and codes against the IFLS codebook."
        )


# ============================================================
# 7. READ AND SAVE CSV FILES
# ============================================================

def read_local_csv(path):

    file_path = project_root() / path

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    # Preserve household and individual IDs as strings.
    return pd.read_csv(file_path, dtype="string")


def save_report(data, filename):

    # Aggregate audit reports may be refreshed on reruns.
    file_path = output_dir() / filename

    data.to_csv(file_path, index=False)

    print("Audit report:", file_path)

    return file_path


def save_private(data, filename):

    file_path = intermediate_dir() / filename

    # Avoid accidentally overwriting constructed private data.
    if file_path.exists():
        raise FileExistsError(
            f"Private file already exists: {file_path}. "
            "Back it up before rebuilding."
        )

    data.to_csv(file_path, index=False)

    print("Created private file:", file_path)

    return file_path
