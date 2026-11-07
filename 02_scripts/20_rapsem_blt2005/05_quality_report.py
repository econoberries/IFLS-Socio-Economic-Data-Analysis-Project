"""
05_quality_report.py

Check the quality of the person panel created by 04_build_panel.py.

This script:
1. Counts observed and missing values for every column.
2. Calculates the percentage of missing values.
3. Counts distinct observed values.
4. Summarizes treatment, poverty, and sample-selection indicators.
5. Saves two aggregate CSV reports.

This script only reads the private panel. It never edits the data or
exports individual-level records. These are descriptive checks, not
causal estimates.
"""

import pandas as pd

from common import intermediate_dir, save_report


# ============================================================
# 1. VARIABLE COMPLETENESS
# ============================================================

def check_completeness(panel):

    results = []
    total = len(panel)

    for column in panel.columns:
        observed = int(panel[column].notna().sum())
        missing = int(panel[column].isna().sum())

        results.append({
            "variable": column,
            "n_total": total,
            "n_observed": observed,
            "n_missing": missing,
            "missing_pct": round(missing / total * 100, 2),
            "unique_values": int(panel[column].nunique(dropna=True)),
        })

    report = pd.DataFrame(results)
    return report.sort_values("missing_pct", ascending=False)


# ============================================================
# 2. TREATMENT AND SAMPLE-SELECTION COUNTS
# ============================================================

def check_selection(panel):

    variables = [
        "blt_2005",
        "baseline_poor",
        "eligible_all_core",
        "poor_ifls3",
        "poor_ifls5",
        "poverty_exit_2014",
        "observed_ifls4",
        "observed_ifls5",
        "observed_cesd",
        "cesd_observed_items",
        "cesd_complete_10",
    ]

    results = []

    for column in variables:

        if column not in panel.columns:
            print(f"Skipping missing column: {column}")
            continue

        # Count every value, including missing responses.
        counts = panel[column].fillna("<MISSING>").value_counts()

        for value, count in counts.items():
            results.append({
                "variable": column,
                "value": value,
                "n": int(count),
            })

    return pd.DataFrame(results, columns=["variable", "value", "n"])


# ============================================================
# 3. LOAD THE PANEL AND SAVE REPORTS
# ============================================================

def main():

    panel_path = intermediate_dir() / "person_panel_full.csv"

    if not panel_path.exists():
        raise FileNotFoundError(
            "Panel file not found. Complete the approved 04_build_panel.py "
            "workflow before running the quality report."
        )

    # Strings keep identifiers and codes unchanged when reading the file.
    panel = pd.read_csv(panel_path, dtype="string")

    if panel.empty:
        raise ValueError("The panel file contains no observations.")

    print("\n=== PANEL OVERVIEW ===")
    print(f"Individuals: {len(panel):,}")
    print(f"Variables: {len(panel.columns):,}")

    # Report 1: missingness for every variable.
    completeness = check_completeness(panel)

    print("\n=== VARIABLE COMPLETENESS ===")
    print(completeness.to_string(index=False))

    save_report(completeness, "05_variable_completeness.csv")

    # Report 2: distributions of selected categorical variables.
    selection = check_selection(panel)

    print("\n=== TREATMENT AND SAMPLE SELECTION ===")

    if not selection.empty:
        print(selection.to_string(index=False))
        save_report(selection, "05_selection_and_treatment_counts.csv")
    else:
        print("No selected variables were found in the panel.")

    print("\nPanel quality checks completed.")
    print("Review missingness, sample loss, and treatment classification.")
    print("These summaries do not establish causal identification.")


if __name__ == "__main__":
    main()
