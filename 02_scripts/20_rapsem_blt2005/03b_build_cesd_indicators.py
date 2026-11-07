"""
03b_build_cesd_indicators.py — PROVISIONAL IFLS4 CES-D item construction.

The IFLS4 Book 3B KP questionnaire (p. 12) establishes:
  KP01: 1=yes (ask KP02), 3=no (skip KP02).
  KP02: 1=rarely/<=1 day, 2=1–2 days, 3=3–4, 4=5–7 days.
  KPTYPE: A through J. E (hopeful) and H (happy) are positive items.

Researcher-proposed mapping of an observed item to distress (0–3):
  KP01=3 and KP02 blank -> raw frequency 0;
  KP01=1 and KP02 in 1–4 -> raw frequency KP02-1;
  invalid, inconsistent, or special codes -> missing.
  Reverse positive items E and H: 3 - raw frequency.

The source verifies the survey responses, NOT that this derived ordinal
scoring has measurement invariance or is validated for an SEM. No total
score or latent factor is estimated.

Runs from the project root. Original Stata files are never changed.
Default: aggregate reports only.
Optional: --write-private saves wide person-level candidates to ignored
          01_data/04_intermediate/rapsem_blt2005/; no overwrite.

    python 02_scripts/20_rapsem_blt2005/03b_build_cesd_indicators.py
    python 02_scripts/20_rapsem_blt2005/03b_build_cesd_indicators.py --write-private
"""

import argparse

import pandas as pd

from common import normalized, require_columns, save_private, save_report, stata


ITEMS = tuple("ABCDEFGHIJ")
POSITIVE_ITEMS = {"E", "H"}


def build_cesd(df):
    """Return aggregate-ready item table and local private-wide candidates."""
    require_columns(df, ["pidlink", "kptype", "kp01", "kp02"], "IFLS4 b3b_kp")

    frame = pd.DataFrame(index=df.index)
    frame["pidlink"] = normalized(df["pidlink"])
    frame["kptype"] = normalized(df["kptype"])
    frame["kp01"] = normalized(df["kp01"])
    frame["kp02"] = normalized(df["kp02"])

    if frame["pidlink"].isna().any():
        raise ValueError("Missing PIDLINK in KP; do not discard records silently.")
    if not frame["kptype"].isin(ITEMS).all():
        raise ValueError("Unknown/missing KPTYPE. Audit before deriving CES-D.")
    if frame.duplicated(["pidlink", "kptype"]).any():
        raise ValueError("Duplicate PIDLINK x KPTYPE; do not pivot arbitrarily.")

    by_person = frame.groupby("pidlink")["kptype"].agg(["size", "nunique"])
    if not (by_person["size"].eq(10) & by_person["nunique"].eq(10)).all():
        raise ValueError("Not every person has exactly ten unique A-J rows.")

    no = frame["kp01"].eq("3").fillna(False)
    yes = frame["kp01"].eq("1").fillna(False)
    skip = no & frame["kp02"].isna()
    valid_yes = yes & frame["kp02"].isin(["1", "2", "3", "4"]).fillna(False)

    frame["coding_reason"] = "unverified_or_special_code"
    frame.loc[no & frame["kp02"].notna(), "coding_reason"] = "inconsistent_no_with_frequency"
    frame.loc[yes & ~valid_yes, "coding_reason"] = "yes_frequency_missing_or_special"
    frame.loc[skip, "coding_reason"] = "valid_no_skip"
    frame.loc[valid_yes, "coding_reason"] = "valid_yes_frequency"

    frequency = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    frequency.loc[skip] = 0
    frequency.loc[valid_yes] = (
        pd.to_numeric(frame.loc[valid_yes, "kp02"]) - 1
    ).astype("Int64")
    frame["frequency_0_3"] = frequency

    positive = frame["kptype"].isin(POSITIVE_ITEMS)
    distress = frequency.copy()
    distress.loc[positive] = 3 - distress.loc[positive]
    frame["distress_0_3_candidate"] = distress

    wide = frame.pivot(
        index="pidlink", columns="kptype", values="distress_0_3_candidate"
    ).rename(columns={item: f"cesd_{item}" for item in ITEMS})
    wide = wide[[f"cesd_{item}" for item in ITEMS]]
    wide["cesd_valid_items"] = wide.notna().sum(axis=1)
    wide["cesd_complete_10"] = wide["cesd_valid_items"].eq(10)
    wide = wide.reset_index()
    return frame, wide


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-private", action="store_true",
        help="Save candidate PIDLINK-level item scores locally; refuse to overwrite."
    )
    args = parser.parse_args()

    source, _ = stata("ifls4", "b3b_kp")
    source.columns = source.columns.str.lower()
    frame, wide = build_cesd(source)

    print("\n=== CES-D: CANDIDATE ITEM CODING ===")
    patterns = (
        frame.groupby(["kptype", "coding_reason"], dropna=False)
        .size().reset_index(name="n_responses")
        .sort_values(["kptype", "n_responses"], ascending=[True, False])
    )
    print(patterns.to_string(index=False))
    save_report(patterns, "03b_cesd_coding_reasons.csv")

    scores = (
        frame.assign(
            score_code=frame["distress_0_3_candidate"]
            .astype("string").fillna("<MISSING>")
        )
        .groupby(["kptype", "score_code"], dropna=False)
        .size().reset_index(name="n_responses")
    )
    save_report(scores, "03b_cesd_candidate_score_frequencies.csv")

    person_counts = (
        wide["cesd_valid_items"].value_counts(dropna=False)
        .rename_axis("valid_items")
        .reset_index(name="n_people")
        .sort_values("valid_items")
    )
    print("\n=== VALID DISTRESS INDICATORS PER PERSON ===")
    print(person_counts.to_string(index=False))
    save_report(person_counts, "03b_cesd_candidate_person_completeness.csv")

    if args.write_private:
        save_private(
            wide, "cesd2007_candidate_items_wide.csv"
        )
    else:
        print("\nNo person-level data exported. Use --write-private after review.")

    print(
        "STOP: provisional scoring, not an approved CES-D latent mediator. "
        "Check codebook special codes, item distributions and CFA assumptions."
    )


if __name__ == "__main__":
    main()
