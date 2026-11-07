"""
03_build_welfare.py

Build household welfare variables using IFLS3 and IFLS5.

Main outputs:
1. Monthly household expenditure
2. Monthly per capita expenditure (PCE)
3. Log PCE relative to the poverty line
4. Household poverty status

Important:
- Original IFLS data are never modified.
- Consumption items and poverty lines must be verified first.
- Incomplete expenditure information is not treated as zero.
- Existing private output files are never overwritten.

See README_welfare_formulas.md for formulas and questionnaire checks.
"""

import json
import numpy as np
import pandas as pd

from common import (
    script_dir,
    project_root,
    read_config,
    approved,
    stata,
    normalized,
    require_columns,
    assert_unique,
    intermediate_dir,
    save_report,
)


# ============================================================
# 1. LOAD CONFIGURATION
# ============================================================

def load_configuration():
    """Read the verified local JSON settings before building welfare."""

    config_path = script_dir() / "welfare_basket.json"

    if not config_path.exists():
        raise FileNotFoundError(
            "Missing welfare_basket.json. "
            "Copy welfare_basket.example.json and verify its settings."
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    approved(config)

    # The household roster settings are kept in study_config.json.
    roster_config = read_config()["rosters"]

    return config, roster_config


# ============================================================
# 2. CALCULATE HOUSEHOLD SIZE
# ============================================================

def get_household_size(wave, settings):

    approved(settings)

    if not settings["current_codes"]:
        raise ValueError(f"{wave}: Current member codes are missing.")

    # Load the Book K household roster.
    roster, _ = stata(wave, settings["file"])

    required = [
        settings["pid"],
        settings["household"],
        settings["membership"],
    ]
    require_columns(roster, required, f"{wave} roster")

    # Keep only approved current household members.
    current_codes = [str(code) for code in settings["current_codes"]]
    is_current = normalized(roster[settings["membership"]]).isin(
        current_codes
    )
    roster = roster.loc[is_current].copy()

    # Standardize person and household IDs.
    roster["pidlink"] = normalized(roster[settings["pid"]])
    roster["hhid"] = normalized(roster[settings["household"]])
    roster = roster.dropna(subset=["pidlink", "hhid"])

    # Each person should appear only once after filtering.
    assert_unique(roster, "pidlink", f"{wave} current roster")

    household_size = (
        roster.groupby("hhid")
        .size()
        .reset_index(name="household_size")
    )

    return household_size


# ============================================================
# 3. CALCULATE ONE EXPENDITURE COMPONENT
# ============================================================

def get_expenditure(wave, settings, number, missing_codes):

    file_name = settings["file"]
    amount_columns = settings["amount_columns"]

    if not amount_columns:
        raise ValueError(f"{wave} {file_name}: No expenditure columns.")

    # Determine which consumption items to include.
    use_all_rows = settings.get("all_rows_approved", False)

    if not use_all_rows and not settings.get("include_codes"):
        raise ValueError(
            f"{wave} {file_name}: Consumption item codes are not approved."
        )

    # Convert weekly, monthly, or yearly amounts to monthly units.
    monthly_factor = float(settings["multiply_to_monthly"])

    if not np.isfinite(monthly_factor) or monthly_factor <= 0:
        raise ValueError(f"{wave} {file_name}: Invalid monthly factor.")

    data, _ = stata(wave, file_name)

    required = [settings["household"]] + amount_columns

    if not use_all_rows:
        required.append(settings["item_column"])

    require_columns(data, required, f"{wave} {file_name}")

    data = data.copy()
    data["hhid"] = normalized(data[settings["household"]])
    data = data.dropna(subset=["hhid"])

    # Keep only approved consumption categories.
    if not use_all_rows:
        item_codes = [str(code) for code in settings["include_codes"]]
        is_selected = normalized(data[settings["item_column"]]).isin(
            item_codes
        )
        data = data.loc[is_selected].copy()

    if data.empty:
        raise ValueError(f"{wave} {file_name}: No expenditure records.")

    # Convert expenditure columns into numbers.
    missing_codes = [str(code) for code in missing_codes]

    for column in amount_columns:
        values = normalized(data[column])

        # Treat approved special codes as missing values.
        values = values.mask(values.isin(missing_codes))
        data[column] = pd.to_numeric(values, errors="coerce")

        # Set missing to zero only for explicitly approved fields.
        if column in settings.get("zero_if_missing_columns", []):
            data[column] = data[column].fillna(0)

    # A missing required amount makes the item amount missing.
    data["monthly_amount"] = (
        data[amount_columns].sum(
            axis=1,
            min_count=len(amount_columns)
        ) * monthly_factor
    )

    if (data["monthly_amount"].dropna() < 0).any():
        raise ValueError(f"{wave} {file_name}: Negative expenditure found.")

    # Sum selected items for each household.
    expenditure = (
        data.groupby("hhid")
        .agg(
            total=("monthly_amount", lambda x: x.sum(min_count=1)),
            missing=("monthly_amount", lambda x: x.isna().sum()),
        )
        .reset_index()
    )

    component_name = f"part{number}_{file_name}"

    expenditure = expenditure.rename(columns={
        "total": component_name,
        "missing": f"{component_name}_missing",
    })

    audit = {
        "wave": wave,
        "file": file_name,
        "selected_rows": len(data),
        "total_missing_item_values": int(data["monthly_amount"].isna().sum()),
        "households": len(expenditure),
    }

    return expenditure, component_name, audit


# This small helper is used in Section 7 and by our synthetic tests.
def calculate_poverty(welfare):

    ratio = welfare["monthly_pce"] / welfare["monthly_poverty_line"]

    # The logarithm exists only for a positive ratio.
    welfare["log_pce_pl"] = np.log(ratio.where(ratio > 0))

    welfare["poor"] = (
        (welfare["log_pce_pl"] < 0)
        .astype("Int64")
        .where(welfare["log_pce_pl"].notna())
    )

    return welfare


def main():

    # Run Section 1: load the two local configuration files.
    config, roster_config = load_configuration()

    # ========================================================
    # 4. BUILD HOUSEHOLD EXPENDITURE FOR EACH WAVE
    # ========================================================

    all_waves = []
    audit_results = []

    for wave in ["ifls3", "ifls5"]:

        print(f"\nProcessing {wave.upper()}...")

        if not config.get(f"basket_complete_{wave}", False):
            raise ValueError(
                f"{wave}: Complete consumption basket is not approved. "
                "Check all relevant KS items, including KS0."
            )

        components = config["components"][wave]

        if not components:
            raise ValueError(f"{wave}: No expenditure components.")

        # Start with household sizes.
        household = get_household_size(wave, roster_config[wave])

        expenditure_columns = []
        missing_columns = []

        # Calculate each approved expenditure component.
        for number, settings in enumerate(components, start=1):

            expenditure, name, audit = get_expenditure(
                wave,
                settings,
                number,
                config.get("missing_codes", []),
            )

            household = household.merge(
                expenditure,
                on="hhid",
                how="left",
                validate="one_to_one",
            )

            expenditure_columns.append(name)
            missing_columns.append(f"{name}_missing")
            audit_results.append(audit)

        # Check whether every required component is observed.
        has_all_components = (
            household[expenditure_columns].notna().all(axis=1)
        )

        # Check whether any selected item contains missing expenditure.
        has_no_missing_items = (
            household[missing_columns]
            .fillna(1)
            .eq(0)
            .all(axis=1)
        )

        complete = has_all_components & has_no_missing_items

        # Calculate total monthly household expenditure.
        household["monthly_total_expenditure"] = (
            household[expenditure_columns]
            .sum(axis=1, min_count=len(expenditure_columns))
            .where(complete)
        )

        # Calculate per capita expenditure (PCE).
        household["monthly_pce"] = (
            household["monthly_total_expenditure"]
            / household["household_size"]
        )

        household["wave"] = wave
        all_waves.append(household)

        print(f"Households: {len(household):,}")
        print(f"With complete expenditure: {int(complete.sum()):,}")

    # ========================================================
    # 5. COMBINE IFLS3 AND IFLS5
    # ========================================================

    welfare = pd.concat(all_waves, ignore_index=True)

    # ========================================================
    # 6. LOAD AND MERGE VERIFIED POVERTY LINES
    # ========================================================

    poverty_path = project_root() / config["poverty_lines_file"]

    if not poverty_path.exists():
        raise FileNotFoundError(
            f"Missing verified poverty line file: {poverty_path}"
        )

    poverty_lines = pd.read_csv(poverty_path, dtype="string")

    require_columns(
        poverty_lines,
        ["wave", "hhid", "monthly_poverty_line"],
        "poverty line dataset",
    )

    poverty_lines["wave"] = normalized(poverty_lines["wave"])
    poverty_lines["hhid"] = normalized(poverty_lines["hhid"])

    # Each household must have at most one poverty line per survey wave.
    if poverty_lines[["wave", "hhid"]].isna().any().any():
        raise ValueError("Poverty line identifiers are missing.")

    if poverty_lines.duplicated(["wave", "hhid"]).any():
        raise ValueError("Duplicate household poverty lines found.")

    poverty_lines["monthly_poverty_line"] = pd.to_numeric(
        poverty_lines["monthly_poverty_line"],
        errors="coerce",
    )

    if (poverty_lines["monthly_poverty_line"].dropna() <= 0).any():
        raise ValueError("Poverty lines must be positive.")

    welfare = welfare.merge(
        poverty_lines[["wave", "hhid", "monthly_poverty_line"]],
        on=["wave", "hhid"],
        how="left",
        validate="one_to_one",
    )

    # ========================================================
    # 7. CALCULATE POVERTY VARIABLES
    # ========================================================

    welfare = calculate_poverty(welfare)

    # ========================================================
    # 8. CREATE AUDIT REPORTS
    # ========================================================

    summary = (
        welfare.groupby("wave")
        .agg(
            households=("hhid", "size"),
            with_valid_welfare=("log_pce_pl", "count"),
            median_pce=("monthly_pce", "median"),
        )
        .reset_index()
    )

    save_report(
        pd.DataFrame(audit_results),
        "03_welfare_component_audit.csv",
    )

    save_report(summary, "03_welfare_summary.csv")

    print("\n=== WELFARE SUMMARY ===")
    print(summary.to_string(index=False))

    # ========================================================
    # 9. SAVE THE FINAL WELFARE DATASET
    # ========================================================

    output_path = intermediate_dir() / "household_welfare_harmonized.csv"

    if output_path.exists():
        raise FileExistsError(
            f"Output already exists: {output_path}. "
            "Back up the old file before rebuilding."
        )

    output_columns = [
        "wave",
        "hhid",
        "monthly_pce",
        "monthly_poverty_line",
        "log_pce_pl",
        "poor",
        "household_size",
    ]

    welfare[output_columns].to_csv(output_path, index=False)

    print("\nWelfare dataset created successfully!")
    print(f"Saved to: {output_path}")
    print("Review the audit reports before using the data.")


if __name__ == "__main__":
    main()
