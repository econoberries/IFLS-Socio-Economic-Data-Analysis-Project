"""
03_build_welfare.py

Calculate household welfare for IFLS3 (2000) and IFLS5 (2014/15).

Outputs:
- Monthly household expenditure
- Monthly per capita expenditure (PCE)
- Log PCE divided by the poverty line
- Poverty status (1 = poor, 0 = not poor)

Before running:
1. Verify the expenditure items and reference periods for both waves.
2. Complete and approve welfare_basket.json.
3. Complete and approve the household roster settings in study_config.json.
4. Supply real, correctly matched household poverty lines.

Original Stata files are never changed. Existing private outputs are not
overwritten. See README_welfare_formulas.md for the formulas and assumptions.
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
# 1. HOUSEHOLD SIZE
# ============================================================

def get_household_size(wave, settings):
    """Count approved current household members from the Book K roster."""

    approved(settings)

    if not settings["current_codes"]:
        raise ValueError(f"{wave}: Current household member codes are missing.")

    roster, _ = stata(wave, settings["file"])

    required_columns = [
        settings["pid"],
        settings["household"],
        settings["membership"],
    ]
    require_columns(roster, required_columns, f"{wave} roster")

    # Keep only the household members approved for expenditure denominators.
    current_codes = [str(code) for code in settings["current_codes"]]
    member_codes = normalized(roster[settings["membership"]])
    roster = roster.loc[member_codes.isin(current_codes)].copy()

    roster["pidlink"] = normalized(roster[settings["pid"]])
    roster["hhid"] = normalized(roster[settings["household"]])
    roster = roster.dropna(subset=["pidlink", "hhid"])

    # Duplicate individuals would produce incorrect household sizes.
    assert_unique(roster, "pidlink", f"{wave} current roster")

    household_size = (
        roster.groupby("hhid")
        .size()
        .reset_index(name="household_size")
    )
    return household_size


# ============================================================
# 2. ONE CONSUMPTION COMPONENT
# ============================================================

def get_expenditure(wave, settings, number, missing_codes):
    """Convert one approved consumption component to monthly expenditure."""

    file_name = settings["file"]
    amount_columns = settings["amount_columns"]

    if not amount_columns:
        raise ValueError(f"{wave} {file_name}: No expenditure columns specified.")

    use_all_rows = settings.get("all_rows_approved", False)

    if not use_all_rows and not settings.get("include_codes"):
        raise ValueError(f"{wave} {file_name}: Consumption item codes not approved.")

    monthly_factor = float(settings["multiply_to_monthly"])

    if not np.isfinite(monthly_factor) or monthly_factor <= 0:
        raise ValueError(f"{wave} {file_name}: Invalid monthly conversion factor.")

    data, _ = stata(wave, file_name)

    required_columns = [settings["household"]] + amount_columns
    if not use_all_rows:
        required_columns.append(settings["item_column"])

    require_columns(data, required_columns, f"{wave} {file_name}")

    data = data.copy()
    data["hhid"] = normalized(data[settings["household"]])
    data = data.dropna(subset=["hhid"])

    # Select only items listed in the verified basket configuration.
    if not use_all_rows:
        item_codes = [str(code) for code in settings["include_codes"]]
        selected = normalized(data[settings["item_column"]]).isin(item_codes)
        data = data.loc[selected].copy()

    if data.empty:
        raise ValueError(f"{wave} {file_name}: No approved expenditure records.")

    # Replace verified special missing codes with NA before converting to numbers.
    missing_codes = [str(code) for code in missing_codes]

    for column in amount_columns:
        values = normalized(data[column])
        values = values.mask(values.isin(missing_codes))
        data[column] = pd.to_numeric(values, errors="coerce")

        # Only a documented, explicitly approved missing-as-zero rule is allowed.
        if column in settings.get("zero_if_missing_columns", []):
            data[column] = data[column].fillna(0)

    # If one required column is missing, the item's total remains missing.
    data["monthly_amount"] = (
        data[amount_columns].sum(axis=1, min_count=len(amount_columns))
        * monthly_factor
    )

    if (data["monthly_amount"].dropna() < 0).any():
        raise ValueError(f"{wave} {file_name}: Negative expenditure detected.")

    # Add recorded consumption items within each household.
    expenditure = (
        data.groupby("hhid")
        .agg(
            total=("monthly_amount", lambda values: values.sum(min_count=1)),
            missing=("monthly_amount", lambda values: values.isna().sum()),
        )
        .reset_index()
    )

    component_name = f"part{number}_{file_name}"
    expenditure = expenditure.rename(
        columns={
            "total": component_name,
            "missing": f"{component_name}_missing",
        }
    )

    audit = {
        "wave": wave,
        "file": file_name,
        "selected_rows": len(data),
        "total_missing_item_values": int(data["monthly_amount"].isna().sum()),
        "households": len(expenditure),
    }

    return expenditure, component_name, audit


# ============================================================
# 3. POVERTY VARIABLES
# ============================================================

def calculate_poverty(welfare):
    """Add log relative welfare and a nullable poverty indicator."""

    ratio = welfare["monthly_pce"] / welfare["monthly_poverty_line"]

    # log(0) and log(negative values) are not valid finite welfare values.
    welfare["log_pce_pl"] = np.log(ratio.where(ratio > 0))

    welfare["poor"] = (
        (welfare["log_pce_pl"] < 0)
        .astype("Int64")
        .where(welfare["log_pce_pl"].notna())
    )

    return welfare


# ============================================================
# 4. MAIN WORKFLOW
# ============================================================

def main():

    # Step 1. Load the verified configuration.
    config_path = script_dir() / "welfare_basket.json"

    if not config_path.exists():
        raise FileNotFoundError(
            "Missing welfare_basket.json. Copy the example file and "
            "verify every item, reference period, and approval flag."
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    approved(config)
    roster_config = read_config()["rosters"]

    all_waves = []
    audit_results = []

    # Step 2. Build monthly household expenditure for each wave.
    for wave in ["ifls3", "ifls5"]:

        print(f"\nProcessing {wave.upper()}...")

        if not config.get(f"basket_complete_{wave}", False):
            raise ValueError(
                f"{wave}: Complete expenditure basket has not been approved. "
                "Check KS0 and other relevant consumption components."
            )

        components = config["components"][wave]

        if not components:
            raise ValueError(f"{wave}: No expenditure components configured.")

        household = get_household_size(wave, roster_config[wave])
        amount_columns = []
        missing_columns = []

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

            amount_columns.append(name)
            missing_columns.append(f"{name}_missing")
            audit_results.append(audit)

        # A household is complete only if each configured component is
        # available and none of its recorded item amounts is missing.
        has_all_components = household[amount_columns].notna().all(axis=1)
        has_no_missing_items = (
            household[missing_columns].fillna(1).eq(0).all(axis=1)
        )
        complete = has_all_components & has_no_missing_items

        household["monthly_total_expenditure"] = (
            household[amount_columns]
            .sum(axis=1, min_count=len(amount_columns))
            .where(complete)
        )

        household["monthly_pce"] = (
            household["monthly_total_expenditure"]
            / household["household_size"]
        )

        household["wave"] = wave
        all_waves.append(household)

        print(f"Households: {len(household):,}")
        print(f"With complete configured expenditure: {int(complete.sum()):,}")

    # Step 3. Combine the two survey waves.
    welfare = pd.concat(all_waves, ignore_index=True)

    # Step 4. Load official, verified poverty lines supplied by the researcher.
    poverty_path = project_root() / config["poverty_lines_file"]

    if not poverty_path.exists():
        raise FileNotFoundError(f"Missing verified poverty line file: {poverty_path}")

    poverty_lines = pd.read_csv(poverty_path, dtype="string")
    require_columns(
        poverty_lines,
        ["wave", "hhid", "monthly_poverty_line"],
        "Poverty line dataset",
    )

    poverty_lines["wave"] = normalized(poverty_lines["wave"])
    poverty_lines["hhid"] = normalized(poverty_lines["hhid"])

    if poverty_lines[["wave", "hhid"]].isna().any().any():
        raise ValueError("Poverty line household IDs or waves are missing.")

    if poverty_lines.duplicated(["wave", "hhid"]).any():
        raise ValueError("Duplicate household poverty line entries found.")

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

    # Step 5. Calculate relative welfare and poverty status.
    welfare = calculate_poverty(welfare)

    # Step 6. Save aggregate audit reports.
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

    # Step 7. Save the private welfare file (never overwrite existing data).
    output_path = intermediate_dir() / "household_welfare_harmonized.csv"

    if output_path.exists():
        raise FileExistsError(
            f"Output already exists: {output_path}. "
            "Back it up before rebuilding."
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

    print("\nPrivate welfare dataset created:", output_path)
    print("STOP: Review basket coverage, interview periods, poverty lines, and")
    print("welfare distributions before using this file in the research panel.")


if __name__ == "__main__":
    main()
