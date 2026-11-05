"""
02c_measurement_validation.py — IFLS4 BLT/CES-D structural checks.

Read-only for source .dta files. Outputs aggregate-only audit CSVs; never
exports household/person identifiers, treatment indicators, or CES-D scores.

Run from the project root after 02b_focused_code_audit.py:
    python 02_scripts/20_rapsem_blt2005/02c_measurement_validation.py

IMPORTANT: Data consistency is not questionnaire/codebook validation. This
script makes NO final decisions about what program A, KSR17, KP01, KP02 or
CES-D item directions mean.
"""

import pandas as pd

from common import normalized, require_columns, save_report, stata


EXPECTED_ITEMS = set("ABCDEFGHIJ")


def codes(series):
    """Preserve observed Stata numeric/string codes, including special codes."""
    return normalized(series).fillna("<MISSING>")


def ifls4(stem):
    data, meta = stata("ifls4", stem)
    data.columns = data.columns.str.lower()
    return data, meta


def program_household_audit():
    print("\n========== 1. IFLS4 CASH-TRANSFER RECORD STRUCTURE ==========")
    data, _ = ifls4("b1_ksr1")
    require_columns(
        data,
        ["hhid07", "ksr3type", "ksr17", "ksr18y", "ksr22y"],
        "IFLS4 b1_ksr1",
    )

    frame = pd.DataFrame({
        "hhid": normalized(data["hhid07"]),
        "program": codes(data["ksr3type"]),
        "receipt_code": codes(data["ksr17"]),
        "first_year": codes(data["ksr18y"]),
        "last_year": codes(data["ksr22y"]),
    })
    identified = frame.loc[frame["hhid"].notna()].copy()

    # One row per household/program is expected for a straightforward design,
    # but never drop duplicates automatically.
    duplicates = identified.duplicated(["hhid", "program"], keep=False)
    duplicate_rows = identified.loc[duplicates]
    conflicts = (
        identified.groupby(["hhid", "program"])["receipt_code"]
        .nunique()
        .gt(1)
        .groupby(level="program")
        .sum()
    )

    results = []
    for program, sub in frame.groupby("program", dropna=False):
        good = sub["hhid"].dropna()
        rows_duplicate = duplicate_rows.loc[
            duplicate_rows["program"].eq(program)
        ]
        results.append({
            "program_code": program,
            "rows": len(sub),
            "unique_nonmissing_households": good.nunique(),
            "missing_hhid_rows": int(sub["hhid"].isna().sum()),
            "duplicate_hhid_program_rows": len(rows_duplicate),
            "households_with_conflicting_receipt_codes": int(
                conflicts.get(program, 0)
            ),
        })

    result = pd.DataFrame(results)
    print(result.to_string(index=False))
    save_report(result, "02c_program_household_structure.csv")

    # A year outside 2005/2006 is NOT automatically a bad response:
    # timing must be interpreted with the documented program definition.
    timing = (
        frame.groupby(
            ["program", "receipt_code", "first_year", "last_year"],
            dropna=False,
        )
        .size()
        .reset_index(name="n")
        .rename(columns={"program": "program_code"})
    )
    save_report(timing, "02c_program_receipt_timing_patterns.csv")

    print(
        "\nCheck program labels, eligibility, reference period, KSR17 meanings, "
        "year special codes and household attribution using the IFLS4 KSR questionnaire."
    )
    return result


def mediator_completeness_audit():
    print("\n========== 2. IFLS4 CES-D RECORD COMPLETENESS ==========")
    data, _ = ifls4("b3b_kp")
    require_columns(data, ["pidlink", "kptype", "kp01", "kp02"], "IFLS4 b3b_kp")

    frame = pd.DataFrame({
        "pid": normalized(data["pidlink"]),
        "item": codes(data["kptype"]),
        "kp01": codes(data["kp01"]),
        "kp02": codes(data["kp02"]),
    })
    missing_pid_rows = int(frame["pid"].isna().sum())
    print(f"Rows with missing PIDLINK: {missing_pid_rows:,}")
    if missing_pid_rows:
        print("WARNING: those rows cannot be assigned to individuals.")

    frame = frame.loc[frame["pid"].notna()].copy()
    frame["unexpected_item"] = ~frame["item"].isin(EXPECTED_ITEMS)
    frame["duplicate_person_item"] = frame.duplicated(
        ["pid", "item"], keep=False
    )

    person = frame.groupby("pid").agg(
        rows=("item", "size"),
        distinct_items=("item", "nunique"),
        duplicate_person_item_rows=("duplicate_person_item", "sum"),
        unexpected_item_rows=("unexpected_item", "sum"),
    )
    person["exactly_one_each_A_to_J"] = (
        person["rows"].eq(10)
        & person["distinct_items"].eq(10)
        & person["duplicate_person_item_rows"].eq(0)
        & person["unexpected_item_rows"].eq(0)
    )

    # Only grouped counts go to disk; no PIDLINK values are saved or printed.
    patterns = (
        person.groupby(
            [
                "rows", "distinct_items", "duplicate_person_item_rows",
                "unexpected_item_rows", "exactly_one_each_A_to_J"
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="n_people")
        .sort_values("n_people", ascending=False)
    )
    print(f"Individuals with a nonmissing PIDLINK: {len(person):,}")
    print(
        "Individuals with one observed row for each of A-J: "
        f"{int(person['exactly_one_each_A_to_J'].sum()):,}"
    )
    print(patterns.head(15).to_string(index=False))
    save_report(patterns, "02c_cesd_person_item_patterns.csv")

    # This confirms an observed response pattern, NOT its intended
    # questionnaire skip rule or the direction of any item.
    responses = (
        frame.groupby(["item", "kp01", "kp02"], dropna=False)
        .size()
        .reset_index(name="n")
        .rename(columns={"item": "kptype_code", "kp01": "kp01_code", "kp02": "kp02_code"})
    )
    save_report(responses, "02c_cesd_screen_frequency_patterns.csv")
    summary = (
        frame.groupby("kp01", dropna=False)
        .agg(
            n_rows=("kp02", "size"),
            n_kp02_missing=("kp02", lambda x: int(x.eq("<MISSING>").sum())),
            n_kp02_present=("kp02", lambda x: int(x.ne("<MISSING>").sum())),
        )
        .reset_index()
        .rename(columns={"kp01": "kp01_code"})
    )
    print("\nObserved KP01 -> KP02 presence (not yet recoded):")
    print(summary.to_string(index=False))
    save_report(summary, "02c_cesd_skip_pattern_summary.csv")

    print(
        "\nVerify all KP01/KP02 responses and skip rules in the questionnaire. "
        "No missing KP02 values are filled, and no score/reverse-score is computed."
    )
    return patterns


def validation_checklist():
    # All of these require manual review against official documentation.
    checks = [
        (
            "Treatment", "KSR3TYPE",
            "Identify the label and dates of each IFLS4 program; distinguish BLT 2005/06 from other programs."
        ),
        (
            "Treatment", "KSR17",
            "Verify all receipt/nonreceipt and special codes, including codes 1, 3, 6 and 9."
        ),
        (
            "Treatment", "KSR18Y/KSR22Y",
            "Check first/last receipt-year reference periods and codes 9998/9999; do not reject dates automatically."
        ),
        (
            "Treatment", "HHID07",
            "Investigate duplicate household-program records and household splitting between 2005 and IFLS4."
        ),
        (
            "Mediator", "KPTYPE",
            "Confirm wording and intended direction for all ten items A-J."
        ),
        (
            "Mediator", "KP01/KP02",
            "Verify screen and skip logic; verify frequency scale, special code 9 and scoring."
        ),
        (
            "Mediator", "PIDLINK",
            "Check exactly ten valid unique item records per person and linkage to the current-member roster."
        ),
    ]
    checklist = pd.DataFrame(
        checks, columns=["component", "variable", "required_manual_verification"]
    )
    checklist["questionnaire_verified"] = "NO"
    checklist["approved_for_analysis"] = "NO"
    save_report(checklist, "02c_manual_codebook_checklist.csv")


def main():
    program_household_audit()
    mediator_completeness_audit()
    validation_checklist()
    print("\n========== MEASUREMENT VALIDATION AUDIT COMPLETE ==========")
    print("Read-only source checks complete; aggregate reports were refreshed.")
    print("STOP: questionnaire mappings and causal treatment assignment remain unapproved.")


if __name__ == "__main__":
    main()
