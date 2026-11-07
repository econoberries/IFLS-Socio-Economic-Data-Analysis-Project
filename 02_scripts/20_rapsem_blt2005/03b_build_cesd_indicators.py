"""
03b_build_cesd_indicators.py

Construct provisional psychological distress indicators from IFLS4.

Source:
    IFLS4 Book 3B, Section KP, page 12
    Dataset: b3b_kp.dta

Important variables:
    KPTYPE : Mental health item (A-J)
    KP01   : Whether the person experienced the feeling
    KP02   : How often the person experienced the feeling

This script:
1. Checks the ten CES-D questionnaire items.
2. Converts responses into frequency scores (0-3).
3. Reverse-scores positive items E and H.
4. Creates one row per individual.
5. Saves aggregate audit reports.

The scoring is provisional, not a validated latent mediator.
Original IFLS data are never modified.
Individual-level data are saved only with --write-private.
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
# 1. DEFINE CES-D ITEMS
# ============================================================

ITEMS = list("ABCDEFGHIJ")

# Feeling hopeful (E) and happy (H) are positive feelings.
POSITIVE_ITEMS = ["E", "H"]


# ============================================================
# 2. CONSTRUCT CES-D INDICATORS
# ============================================================

def build_cesd(data):

    columns = ["pidlink", "kptype", "kp01", "kp02"]
    require_columns(data, columns, "IFLS4 b3b_kp")

    # Keep only the columns we need.
    cesd = data[columns].copy()

    # Standardize all codes to strings, including numeric codes.
    for column in columns:
        cesd[column] = normalized(cesd[column])

    # Check individual IDs and questionnaire item codes.
    if cesd["pidlink"].isna().any():
        raise ValueError("Some individual IDs are missing.")

    if not cesd["kptype"].isin(ITEMS).all():
        raise ValueError("Unknown CES-D item codes found.")

    if cesd.duplicated(["pidlink", "kptype"]).any():
        raise ValueError("Duplicate CES-D items found for a person.")

    # Each individual should have exactly ten distinct A-J items.
    item_counts = cesd.groupby("pidlink")["kptype"].nunique()

    if not item_counts.eq(10).all():
        raise ValueError("Some individuals do not have all ten CES-D items.")

    # --------------------------------------------------------
    # Interpret questionnaire responses.
    # --------------------------------------------------------

    # KP01 = 1: Yes, experienced this feeling.
    # KP01 = 3: No, did not experience this feeling.
    yes = cesd["kp01"].eq("1").fillna(False)
    no = cesd["kp01"].eq("3").fillna(False)

    # If KP01 = 3, the questionnaire tells us to skip KP02.
    valid_skip = no & cesd["kp02"].isna()

    # If KP01 = 1, KP02 must contain one of the four frequencies.
    valid_frequency = (
        yes & cesd["kp02"].isin(["1", "2", "3", "4"])
    )

    # Record why each response can or cannot be scored.
    cesd["coding_reason"] = "unverified_or_special_code"

    cesd.loc[
        no & cesd["kp02"].notna(),
        "coding_reason",
    ] = "inconsistent_no_with_frequency"

    cesd.loc[
        yes & ~valid_frequency,
        "coding_reason",
    ] = "yes_frequency_missing_or_special"

    cesd.loc[valid_skip, "coding_reason"] = "valid_no_skip"
    cesd.loc[valid_frequency, "coding_reason"] = "valid_yes_frequency"

    # --------------------------------------------------------
    # Calculate frequency scores (0-3).
    # --------------------------------------------------------

    # KP01 = 3, KP02 blank    -> 0
    # KP01 = 1, KP02 = 1     -> 0
    # KP01 = 1, KP02 = 2     -> 1
    # KP01 = 1, KP02 = 3     -> 2
    # KP01 = 1, KP02 = 4     -> 3
    # All other combinations -> missing
    cesd["frequency_0_3"] = pd.Series(
        pd.NA,
        index=cesd.index,
        dtype="Int64",
    )

    cesd.loc[valid_skip, "frequency_0_3"] = 0

    cesd.loc[valid_frequency, "frequency_0_3"] = (
        pd.to_numeric(cesd.loc[valid_frequency, "kp02"]) - 1
    ).astype("Int64")

    # --------------------------------------------------------
    # Reverse-score the two positive feelings.
    # --------------------------------------------------------

    cesd["distress_0_3_candidate"] = cesd["frequency_0_3"].copy()

    positive = cesd["kptype"].isin(POSITIVE_ITEMS)

    cesd.loc[positive, "distress_0_3_candidate"] = (
        3 - cesd.loc[positive, "frequency_0_3"]
    )

    # Higher scores now provisionally represent greater distress.

    # --------------------------------------------------------
    # Reshape the data to one row per individual.
    # --------------------------------------------------------

    wide = cesd.pivot(
        index="pidlink",
        columns="kptype",
        values="distress_0_3_candidate",
    )

    # Rename A, B, C ... to cesd_A, cesd_B, cesd_C ...
    wide = wide.rename(
        columns={item: f"cesd_{item}" for item in ITEMS}
    )

    score_columns = [f"cesd_{item}" for item in ITEMS]
    wide = wide[score_columns].copy()

    # Count valid scores, not just available questionnaire rows.
    wide["cesd_valid_items"] = wide[score_columns].notna().sum(axis=1)
    wide["cesd_complete_10"] = wide["cesd_valid_items"].eq(10)

    wide = wide.reset_index()

    return cesd, wide


# ============================================================
# 3. LOAD DATA AND CREATE AUDIT REPORTS
# ============================================================

def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-private",
        action="store_true",
        help="Save the individual-level CES-D candidate dataset locally.",
    )
    args = parser.parse_args()

    # Load the original IFLS4 Stata dataset.
    data, _ = stata("ifls4", "b3b_kp")
    data.columns = data.columns.str.lower()

    cesd, wide = build_cesd(data)

    # --------------------------------------------------------
    # 4. Report valid, skipped, and unusual responses.
    # --------------------------------------------------------

    print("\n=== CES-D RESPONSE PATTERNS ===")

    response_summary = (
        cesd.groupby(["kptype", "coding_reason"], dropna=False)
        .size()
        .reset_index(name="n_responses")
    )

    print(response_summary.to_string(index=False))
    save_report(response_summary, "03b_cesd_coding_reasons.csv")

    # --------------------------------------------------------
    # 5. Report scores and missing values for each item.
    # --------------------------------------------------------

    print("\n=== CES-D SCORE DISTRIBUTIONS ===")

    cesd["score_code"] = (
        cesd["distress_0_3_candidate"]
        .astype("string")
        .fillna("<MISSING>")
    )

    score_summary = (
        cesd.groupby(["kptype", "score_code"], dropna=False)
        .size()
        .reset_index(name="n_responses")
    )

    print(score_summary.to_string(index=False))
    save_report(score_summary, "03b_cesd_candidate_score_frequencies.csv")

    # --------------------------------------------------------
    # 6. Check valid-item completeness per individual.
    # --------------------------------------------------------

    print("\n=== CES-D COMPLETENESS ===")

    completeness = (
        wide["cesd_valid_items"]
        .value_counts(dropna=False)
        .rename_axis("valid_items")
        .reset_index(name="n_people")
        .sort_values("valid_items")
    )

    print(completeness.to_string(index=False))
    save_report(completeness, "03b_cesd_candidate_person_completeness.csv")

    # --------------------------------------------------------
    # 7. Optionally save the private person-level candidate file.
    # --------------------------------------------------------

    if args.write_private:
        save_private(wide, "cesd2007_candidate_items_wide.csv")
    else:
        print("\nNo individual-level data were exported.")

    print("\nCES-D candidate construction completed.")
    print("Review the item distributions and unverified responses.")
    print("These indicators are not yet validated for CFA or RAPSEM.")


if __name__ == "__main__":
    main()
