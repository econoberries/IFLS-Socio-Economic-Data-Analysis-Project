"""
02 — IFLS Candidate Variable Audit

Purpose:
    1. Identify important datasets for our RAPSEM research.
    2. Check which datasets are available.
    3. Read selected variables and their response codes.
    4. Examine BLT and CES-D response frequencies.
    5. Check respondent ID overlap across IFLS waves.
    6. Save summary tables for further investigation.

Notes:
    - Reads original Stata (.dta) files.
    - Does not modify the original datasets.
    - Only exports aggregate information, not individual records.
    - IFLS3 can be added later for the preliminary audit.
    - Does not construct treatment, mediator, or outcome variables.
"""

import pandas as pd

from common import (
    normalized,
    stata,
    find_dta,
    save_report,
    txt,
)


# ============================================================
# 1. DEFINE DATASETS TO INSPECT
# ============================================================

# IFLS3: Baseline characteristics (2000)
# IFLS4: BLT receipt and psychological distress (2007/08)
# IFLS5: Household welfare and follow-up (2014/15)

datasets_to_inspect = {
    "ifls3": [
        "bk_ar1",
        "b1_ks0",
        "b1_ks1",
        "b1_ks2",
        "b1_ks3",
        "b2_kr",
        "b3a_tk",
    ],
    "ifls4": [
        "bk_ar1",
        "b1_ksr1",
        "b1_ksr3",
        "b1_ksr4",
        "b3b_kp",
    ],
    "ifls5": [
        "bk_ar1",
        "b1_ks0",
        "b1_ks1",
        "b1_ks2",
        "b1_ks3",
        "b3b_kp",
    ],
}


# ============================================================
# 2. DEFINE VARIABLES TO EXAMINE
# ============================================================

# Candidate variable meanings and valid codes still require
# verification against the IFLS questionnaires.

selected_variables = [
    "ar01a",       # Household membership

    "kptype",      # CES-D item identifier
    "kp01",        # CES-D screening response
    "kp02",        # CES-D frequency response

    "ksr3type",    # Cash-transfer / assistance program
    "ksr1type",
    "ksr2type",

    "ksr17",       # Candidate receipt response
    "ksr18y",      # Candidate first receipt year
    "ksr18m",
    "ksr22y",      # Candidate last receipt year
    "ksr22m",
]

# Collect only aggregate results and unfiltered ID sets in memory.
file_summary = []
response_frequencies = []
respondent_ids = {}
missing_datasets = []


# ============================================================
# 3. CHECK AND READ THE SELECTED DATASETS
# ============================================================

for wave, datasets in datasets_to_inspect.items():

    print("\n" + "=" * 55)
    print(f"CHECKING {wave.upper()}")
    print("=" * 55)

    for dataset in datasets:

        file_path = find_dta(
            wave,
            dataset,
            required=False,
        )

        if file_path is None:
            print(f"Missing dataset: {dataset}.dta")
            missing_datasets.append(f"{wave}/{dataset}.dta")
            continue

        print(f"\nReading: {dataset}.dta")

        # Read the original Stata dataset and its labels.
        data, metadata = stata(wave, dataset)

        # One summary row per inspected dataset.
        file_summary.append({
            "wave": wave,
            "file": dataset,
            "rows": len(data),
            "columns": len(data.columns),
            "unique_pidlinks": None,
            "duplicate_pidlinks": None,
        })

        print(f"  Rows: {len(data):,}")
        print(f"  Columns: {len(data.columns):,}")

        # ====================================================
        # 4. EXAMINE RESPONSE CODES AND VALUE LABELS
        # ====================================================

        value_labels = metadata.variable_value_labels or {}

        # Include selected variables and other KP/KSR fields.
        columns_to_check = [
            variable
            for variable in data.columns
            if (
                variable.lower() in selected_variables
                or variable.lower().startswith(("ksr", "kp"))
            )
        ]

        for variable in columns_to_check:

            responses = normalized(data[variable])
            responses = responses.fillna("<MISSING>")

            # Keep ALL observed categories for our selected variables.
            # Special or rare codes may be important for the audit.
            if variable.lower() in selected_variables:
                frequencies = responses.value_counts()
            else:
                # Wider exploratory scan: retain the top 50 categories.
                frequencies = responses.value_counts().head(50)

            labels = {
                txt(code): str(label)
                for code, label in value_labels.get(variable, {}).items()
            }

            for code, count in frequencies.items():

                response_frequencies.append({
                    "wave": wave,
                    "file": dataset,
                    "variable": variable,
                    "code": code,
                    "label": labels.get(code, ""),
                    "n": int(count),
                })

        print(f"  Variables audited: {len(columns_to_check)}")

        # ====================================================
        # 5. CHECK RESPONDENT IDS IN THE HOUSEHOLD ROSTER
        # ====================================================

        if dataset == "bk_ar1":

            if "pidlink" not in data.columns:
                print("  Warning: PIDLINK not found.")
                continue

            ids = normalized(data["pidlink"]).dropna()

            unique_count = ids.nunique()
            duplicate_count = ids.duplicated().sum()

            # Sets are used only in memory for aggregate overlap counts.
            respondent_ids[wave] = set(ids)

            file_summary[-1]["unique_pidlinks"] = int(unique_count)
            file_summary[-1]["duplicate_pidlinks"] = int(duplicate_count)

            print(f"  Unique PIDLINKs: {unique_count:,}")
            print(f"  Repeated PIDLINK rows: {duplicate_count:,}")


# ============================================================
# 6. SAVE DATASET AND RESPONSE CODE SUMMARIES
# ============================================================

save_report(
    pd.DataFrame(
        file_summary,
        columns=[
            "wave",
            "file",
            "rows",
            "columns",
            "unique_pidlinks",
            "duplicate_pidlinks",
        ],
    ),
    "02_critical_file_counts.csv",
)

save_report(
    pd.DataFrame(
        response_frequencies,
        columns=[
            "wave",
            "file",
            "variable",
            "code",
            "label",
            "n",
        ],
    ),
    "02_response_code_frequencies.csv",
)


# ============================================================
# 7. CHECK RESPONDENT OVERLAP BETWEEN SURVEY WAVES
# ============================================================

wave_pairs = [
    ("ifls3", "ifls4"),
    ("ifls4", "ifls5"),
    ("ifls3", "ifls5"),
]

panel_overlap = []

for first_wave, second_wave in wave_pairs:

    # Compare only waves with available roster datasets.
    if first_wave not in respondent_ids:
        continue

    if second_wave not in respondent_ids:
        continue

    common_ids = (
        respondent_ids[first_wave]
        & respondent_ids[second_wave]
    )

    panel_overlap.append({
        "waves": f"{first_wave}-{second_wave}",
        "overlap_unfiltered": len(common_ids),
    })

    print(
        f"\n{first_wave.upper()} - {second_wave.upper()}: "
        f"{len(common_ids):,} overlapping PIDLINKs"
    )

save_report(
    pd.DataFrame(
        panel_overlap,
        columns=["waves", "overlap_unfiltered"],
    ),
    "02_unfiltered_pidlink_overlap.csv",
)


# ============================================================
# 8. PRINT FINAL SUMMARY
# ============================================================

print("\n" + "=" * 55)
print("IFLS CANDIDATE VARIABLE AUDIT COMPLETED")
print("=" * 55)

print(f"\nDatasets inspected: {len(file_summary):,}")
print(f"Datasets not found: {len(missing_datasets):,}")
print(f"Response categories recorded: {len(response_frequencies):,}")
print(f"Wave comparisons completed: {len(panel_overlap):,}")

if missing_datasets:
    print("\nMissing candidate datasets:")
    for dataset in missing_datasets:
        print(f"  {dataset}")

print("\nReports saved to:")
print("05_outputs/tables/rapsem_blt2005/")

print("\nIMPORTANT NOTES:")

print(
    "1. PIDLINK overlap is not yet the final linked sample. "
    "Current household membership must be verified."
)

print(
    "2. Verify IFLS4 KSR response codes before identifying "
    "BLT 2005–2006 recipients."
)

print(
    "3. Verify KPTYPE, KP01, and KP02 codes before constructing "
    "the CES-D psychological distress mediator."
)

print(
    "4. Missing IFLS3 data is acceptable for this preliminary audit. "
    "IFLS3 baseline data are required for the planned longitudinal panel."
)

print("\nNext step:")
print("Review the response-code frequencies and panel overlap.")
