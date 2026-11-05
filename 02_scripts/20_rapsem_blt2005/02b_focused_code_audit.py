"""
02b_focused_code_audit.py

Inspect IFLS4 cash-transfer and psychological-distress response patterns.
Read-only with respect to the original .dta files. Saves aggregate tables only.

Run from the project root:
    python 02_scripts/20_rapsem_blt2005/02b_focused_code_audit.py
"""

import pandas as pd
from common import normalized, save_report, stata


# 1. Helpers for readable, missing-aware frequency tables.
def code_strings(series):
    return normalized(series).fillna("<MISSING>")


def print_labels(metadata, columns):
    variable_labels = {
        str(key).lower(): value
        for key, value in (metadata.column_names_to_labels or {}).items()
    }
    response_labels = {
        str(key).lower(): value
        for key, value in (metadata.variable_value_labels or {}).items()
    }

    for name in columns:
        print(f"  {name}: {variable_labels.get(name, '(no variable label)')}")
        labels = response_labels.get(name, {})
        if labels:
            print(f"    Value labels: {labels}")


def cross_tab(df, first, second, section):
    """Print a crosstab and return a tidy, aggregate-only table."""
    if first not in df.columns or second not in df.columns:
        absent = [v for v in (first, second) if v not in df.columns]
        print(f"\n{section}: unavailable; missing variable(s): {absent}")
        return pd.DataFrame(
            columns=["section", "group_variable", "group_code",
                     "response_variable", "response_code", "n"]
        )

    a = code_strings(df[first])
    b = code_strings(df[second])

    print(f"\n=== {section}: {first.upper()} x {second.upper()} ===")
    print(pd.crosstab(a, b).to_string())

    counts = (
        pd.DataFrame({"group_code": a, "response_code": b})
        .groupby(["group_code", "response_code"])
        .size()
        .reset_index(name="n")
    )
    counts.insert(0, "section", section)
    counts.insert(1, "group_variable", first)
    counts.insert(3, "response_variable", second)
    return counts


def main():
    # 2. Cash-transfer program and receipt-year patterns.
    print("\n========== IFLS4 CASH TRANSFERS ==========")
    ksr, ksr_meta = stata("ifls4", "b1_ksr1")
    ksr.columns = ksr.columns.str.lower()

    print("\nVariable labels and available Stata value labels:")
    print_labels(ksr_meta, ["ksr3type", "ksr17", "ksr18y", "ksr22y"])

    treatment_tables = [
        cross_tab(ksr, "ksr3type", "ksr17", "program_by_receipt"),
        cross_tab(ksr, "ksr3type", "ksr18y", "program_by_first_year"),
        cross_tab(ksr, "ksr3type", "ksr22y", "program_by_last_year"),
    ]
    treatment = pd.concat(treatment_tables, ignore_index=True)
    save_report(treatment, "02b_treatment_code_crosstabs.csv")

    # 3. Psychological distress item and response patterns.
    print("\n========== IFLS4 PSYCHOLOGICAL DISTRESS ==========")
    kp, kp_meta = stata("ifls4", "b3b_kp")
    kp.columns = kp.columns.str.lower()

    print("\nVariable labels and available Stata value labels:")
    print_labels(kp_meta, ["kptype", "kp01", "kp02"])

    mediator_tables = [
        cross_tab(kp, "kp01", "kp02", "screening_by_frequency"),
        cross_tab(kp, "kptype", "kp02", "item_by_frequency"),
    ]
    mediator = pd.concat(mediator_tables, ignore_index=True)
    save_report(mediator, "02b_mediator_code_crosstabs.csv")

    if "kp01" not in kp.columns:
        print(
            "\nKP01 is not present in b3b_kp. Do NOT infer why KP02 is "
            "missing from this file alone; consult the IFLS4 questionnaire."
        )

    # 4. Missing KP02 values, separately for every item.
    print("\n=== KP02 RAW MISSINGNESS BY ITEM ===")
    if {"kptype", "kp02"}.issubset(kp.columns):
        items = pd.DataFrame({
            "item": code_strings(kp["kptype"]),
            "kp02_is_null": kp["kp02"].isna(),
        })
        summary = (
            items.groupby("item", as_index=False)
            .agg(
                total=("kp02_is_null", "size"),
                raw_missing=("kp02_is_null", "sum"),
            )
        )
        summary["raw_nonmissing"] = summary["total"] - summary["raw_missing"]
        summary["missing_pct"] = (
            100 * summary["raw_missing"] / summary["total"]
        ).round(1)
        print(summary.to_string(index=False))
        save_report(summary, "02b_mediator_item_missingness.csv")
    else:
        print("KPTYPE or KP02 is absent; missingness table not generated.")

    print(
        "\nDone. Counts are descriptive only: do not code BLT receipt or "
        "CES-D scores until questionnaire response codes are verified."
    )


if __name__ == "__main__":
    main()
