"""
03a_build_blt_treatment.py — PROVISIONAL IFLS4 BLT household treatment.

The IFLS4 Book 1 KSR questionnaire (p. 9) establishes:
  KSR3TYPE A = Bantuan Langsung Tunai (unconditional cash transfer)
  KSR17: 1 = yes, 3 = no; other codes require review
  KSR18Y = year of first receipt, KSR22Y = year of last receipt

A reported "yes" with first receipt in 2005 or 2006 is a candidate for
2005–2006 BLT exposure. Other/unknown dates are NOT coded as controls.
The resulting indicator is not an approved historical household assignment.

Runs from the project root. Original Stata files are never changed.
Default: aggregate reports only (no household data exported).
Optional: --write-private saves candidate household records to ignored
          01_data/04_intermediate/rapsem_blt2005/; never overwrites.

    python 02_scripts/20_rapsem_blt2005/03a_build_blt_treatment.py
    python 02_scripts/20_rapsem_blt2005/03a_build_blt_treatment.py --write-private
"""
import argparse

import pandas as pd

from common import normalized, require_columns, save_private, save_report, stata


def classify_blt(df):
    """Return private, non-approved HHID07-level records and check anomalies."""
    needed = ["hhid07", "ksr3type", "ksr17", "ksr18y", "ksr22y"]
    require_columns(df, needed, "IFLS4 b1_ksr1")
    df = df.loc[normalized(df["ksr3type"]).eq("A")].copy()
    if df.empty:
        raise ValueError("No program-A records found; verify KSR3TYPE in IFLS4.")

    out = pd.DataFrame(index=df.index)
    out["hhid07"] = normalized(df["hhid07"])
    if out["hhid07"].isna().any() or out["hhid07"].duplicated().any():
        raise ValueError("Missing/duplicate HHID07 within BLT program A. Stop; investigate.")

    for col in ["ksr3type", "ksr17", "ksr18y", "ksr22y"]:
        out[col] = normalized(df[col])

    yes = out["ksr17"].eq("1").fillna(False)
    no = out["ksr17"].eq("3").fillna(False)
    first = out["ksr18y"]
    expected_first = first.isin(["2005", "2006"]).fillna(False)

    out["classification"] = "unknown_or_special_receipt_code"
    out.loc[no, "classification"] = "reported_no"
    out.loc[yes & expected_first, "classification"] = "yes_first_2005_or_2006"
    other_year = pd.to_numeric(first, errors="coerce")
    plausible_other = other_year.between(1900, 2100).fillna(False) & ~expected_first
    out.loc[yes & plausible_other, "classification"] = "yes_first_other_year"
    out.loc[yes & ~expected_first & ~plausible_other,
            "classification"] = "yes_first_year_missing_or_special"

    out["blt_2005_06_candidate"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    out.loc[no, "blt_2005_06_candidate"] = 0
    out.loc[yes & expected_first, "blt_2005_06_candidate"] = 1

    last_year = pd.to_numeric(out["ksr22y"], errors="coerce")
    first_year = pd.to_numeric(out["ksr18y"], errors="coerce")
    valid_first = first_year.where(first_year.between(1900, 2100))
    valid_last = last_year.where(last_year.between(1900, 2100))
    out["last_before_first"] = (
        valid_first.notna() & valid_last.notna() & valid_last.lt(valid_first)
    )
    out["nonreceipt_with_date"] = (
        no & (out["ksr18y"].notna() | out["ksr22y"].notna())
    )
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-private", action="store_true",
        help="Save candidate HHID-level file locally; refuse to overwrite."
    )
    args = parser.parse_args()

    source, _ = stata("ifls4", "b1_ksr1")
    source.columns = source.columns.str.lower()
    out = classify_blt(source)

    print("\n=== BLT PROGRAM A: CANDIDATE CLASSIFICATION ===")
    summary = (
        out.groupby(["classification", "ksr17"], dropna=False)
        .size().reset_index(name="n_households")
        .rename(columns={"ksr17": "ksr17_code"})
        .sort_values("n_households", ascending=False)
    )
    print(summary.to_string(index=False))
    save_report(summary, "03a_blt_candidate_classification.csv")

    dates = (
        out.groupby(["classification", "ksr18y", "ksr22y"], dropna=False)
        .size().reset_index(name="n_households")
        .rename(columns={"ksr18y": "first_year", "ksr22y": "last_year"})
    )
    save_report(dates, "03a_blt_candidate_year_patterns.csv")

    quality = pd.DataFrame([
        {"check": "program_A_households", "n": len(out)},
        {"check": "candidate_treated_2005_06",
         "n": int(out["blt_2005_06_candidate"].eq(1).sum())},
        {"check": "reported_nonrecipients",
         "n": int(out["blt_2005_06_candidate"].eq(0).sum())},
        {"check": "unclassified_households",
         "n": int(out["blt_2005_06_candidate"].isna().sum())},
        {"check": "last_year_before_first_year",
         "n": int(out["last_before_first"].sum())},
        {"check": "reported_no_but_year_recorded",
         "n": int(out["nonreceipt_with_date"].sum())},
    ])
    print("\n=== DATA QUALITY ===")
    print(quality.to_string(index=False))
    save_report(quality, "03a_blt_candidate_quality.csv")

    if args.write_private:
        save_private(
            out.reset_index(drop=True),
            "blt2005_candidate_household_ifls4.csv",
        )
    else:
        print("\nNo household-level data exported. Use --write-private only after review.")

    print(
        "STOP: these are candidates, not an approved BLT 2005–06 exposure. "
        "Verify historical household changes, selection, and ambiguous dates."
    )


if __name__ == "__main__":
    main()
