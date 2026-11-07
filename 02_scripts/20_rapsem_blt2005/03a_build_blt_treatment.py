"""
03a_build_blt_treatment.py

Identify households that received BLT in IFLS4.

Source:
    IFLS4 Book 1, Section KSR, page 9
    Dataset: b1_ksr1.dta

Important variables:
    KSR3TYPE = A : BLT (unconditional cash transfer)
    KSR17 = 1    : Received BLT
    KSR17 = 3    : Did not receive BLT
    KSR18Y       : Year of first receipt
    KSR22Y       : Year of last receipt

This script:
1. Selects households in the BLT program.
2. Classifies reported BLT receipt in 2005-2006.
3. Checks unusual responses and receipt years.
4. Saves summary reports.

Original IFLS data are never modified.
Household-level data are saved only with --write-private.
"""

import argparse
import pandas as pd

from common import (
    stata,
    normalized,
    require_columns,
    save_report,
    save_private,
)


# ============================================================
# 1. CLASSIFY BLT RECIPIENTS
# ============================================================

def classify_blt(data):

    # Variables needed from IFLS4
    columns = [
        "hhid07",
        "ksr3type",
        "ksr17",
        "ksr18y",
        "ksr22y",
    ]

    require_columns(data, columns, "IFLS4 b1_ksr1")

    # Keep only program A (BLT)
    blt = data.loc[
        normalized(data["ksr3type"]) == "A",
        columns
    ].copy()

    if blt.empty:
        raise ValueError("No BLT program A records found.")

    # Standardize variables for easier comparison
    for column in columns:
        blt[column] = normalized(blt[column])

    # Every household should appear only once
    if blt["hhid07"].isna().any():
        raise ValueError("Some household IDs are missing.")

    if blt["hhid07"].duplicated().any():
        raise ValueError("Duplicate household IDs found.")

    # --------------------------------------------------------
    # Identify BLT receipt
    # --------------------------------------------------------

    received = blt["ksr17"].eq("1").fillna(False)
    not_received = blt["ksr17"].eq("3").fillna(False)

    first_year = blt["ksr18y"]

    # Treatment period: 2005-2006
    received_2005_06 = first_year.isin(["2005", "2006"])

    # Identify other reported calendar years
    numeric_year = pd.to_numeric(first_year, errors="coerce")

    other_year = (
        numeric_year.between(1900, 2100)
        & ~received_2005_06
    )

    # --------------------------------------------------------
    # Classify each household
    # --------------------------------------------------------

    blt["classification"] = "unknown_or_special_receipt_code"

    blt.loc[
        not_received, "classification"
    ] = "reported_no"

    blt.loc[
        received & received_2005_06,
        "classification"
    ] = "yes_first_2005_or_2006"

    blt.loc[
        received & other_year,
        "classification"
    ] = "yes_first_other_year"

    blt.loc[
        received & ~received_2005_06 & ~other_year,
        "classification"
    ] = "yes_first_year_missing_or_special"

    # --------------------------------------------------------
    # Create candidate treatment indicator
    # --------------------------------------------------------

    # 1 = Reported BLT receipt, first received in 2005-2006
    # 0 = Reported never receiving BLT
    # NA = Unknown, ambiguous, or different receipt year

    blt["blt_2005_06_candidate"] = pd.Series(
        pd.NA,
        index=blt.index,
        dtype="Int64"
    )

    blt.loc[
        not_received, "blt_2005_06_candidate"
    ] = 0

    blt.loc[
        received & received_2005_06,
        "blt_2005_06_candidate"
    ] = 1

    # --------------------------------------------------------
    # Check possible inconsistencies
    # --------------------------------------------------------

    last_year = pd.to_numeric(
        blt["ksr22y"], errors="coerce"
    )

    # Flag cases where the last receipt predates the first
    blt["last_before_first"] = (
        numeric_year.between(1900, 2100)
        & last_year.between(1900, 2100)
        & (last_year < numeric_year)
    )

    # A nonrecipient should normally not report receipt dates
    blt["nonreceipt_with_date"] = (
        not_received
        & (
            blt["ksr18y"].notna()
            | blt["ksr22y"].notna()
        )
    )

    return blt


# ============================================================
# 2. LOAD IFLS4 DATA AND RUN CLASSIFICATION
# ============================================================

def main():

    # Optional command to save household-level data
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--write-private",
        action="store_true",
        help="Save the household-level candidate dataset."
    )

    args = parser.parse_args()

    # Load the original Stata dataset
    data, _ = stata("ifls4", "b1_ksr1")

    data.columns = data.columns.str.lower()

    # Classify BLT households
    blt = classify_blt(data)

    # --------------------------------------------------------
    # 3. SUMMARY: BLT CLASSIFICATION
    # --------------------------------------------------------

    print("\n=== BLT CLASSIFICATION ===")

    summary = (
        blt.groupby(["classification", "ksr17"], dropna=False)
        .size()
        .reset_index(name="n_households")
        .rename(columns={"ksr17": "ksr17_code"})
        .sort_values("n_households", ascending=False)
    )

    print(summary.to_string(index=False))

    save_report(
        summary,
        "03a_blt_candidate_classification.csv"
    )

    # --------------------------------------------------------
    # 4. SUMMARY: RECEIPT YEARS
    # --------------------------------------------------------

    print("\n=== BLT RECEIPT YEARS ===")

    year_summary = (
        blt.groupby(
            ["classification", "ksr18y", "ksr22y"],
            dropna=False
        )
        .size()
        .reset_index(name="n_households")
    )

    year_summary = year_summary.rename(columns={
        "ksr18y": "first_year",
        "ksr22y": "last_year",
    })

    save_report(
        year_summary,
        "03a_blt_candidate_year_patterns.csv"
    )

    # --------------------------------------------------------
    # 5. DATA QUALITY CHECKS
    # --------------------------------------------------------

    print("\n=== DATA QUALITY CHECKS ===")

    checks = {
        "program_A_households": len(blt),

        "candidate_treated_2005_06": (
            blt["blt_2005_06_candidate"] == 1
        ).sum(),

        "reported_nonrecipients": (
            blt["blt_2005_06_candidate"] == 0
        ).sum(),

        "unclassified_households": (
            blt["blt_2005_06_candidate"].isna()
        ).sum(),

        "last_year_before_first_year": (
            blt["last_before_first"].sum()
        ),

        "reported_no_but_year_recorded": (
            blt["nonreceipt_with_date"].sum()
        ),
    }

    quality = pd.DataFrame({
        "check": list(checks.keys()),
        "n": list(checks.values()),
    })

    print(quality.to_string(index=False))

    save_report(
        quality,
        "03a_blt_candidate_quality.csv"
    )

    # --------------------------------------------------------
    # 6. SAVE HOUSEHOLD DATA (OPTIONAL)
    # --------------------------------------------------------

    if args.write_private:

        save_private(
            blt.reset_index(drop=True),
            "blt2005_candidate_household_ifls4.csv"
        )

    else:
        print("\nHousehold-level data were not exported.")

    print("\nBLT candidate classification completed.")
    print("Review the audit reports before using treatment status.")


# ============================================================
# 7. RUN SCRIPT
# ============================================================

if __name__ == "__main__":
    main()
