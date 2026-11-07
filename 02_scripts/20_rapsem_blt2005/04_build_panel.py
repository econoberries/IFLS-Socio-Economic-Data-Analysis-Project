"""
04_build_panel.py

Link IFLS3 (2000), IFLS4 (2007/08), and IFLS5 (2014/15) by PIDLINK.

Steps:
1. Load current household members from the Book K rosters.
2. Keep IFLS3 baseline adults and approved baseline covariates.
3. Link individuals across the three waves.
4. Add candidate BLT receipt from the private 03a output.
5. Add ten candidate CES-D indicators from the private 03b output.
6. Add the approved IFLS3 and IFLS5 household welfare file.
7. Report sample loss and save private panel files.

IMPORTANT: This creates a descriptive candidate panel, not a causal estimate.
All approval checks remain required, especially the historical assignment
of 2005-06 BLT exposure to people found in IFLS4 households.
Do not run until 03a/03b outputs and household welfare are verified.
"""

import numpy as np
import pandas as pd

from common import (
    read_config,
    approved,
    stata,
    normalized,
    require_columns,
    assert_unique,
    read_local_csv,
    save_report,
    save_private,
    intermediate_dir,
    analysis_dir,
)


# ============================================================
# 1. LOAD ONE SURVEY ROSTER
# ============================================================

def load_roster(wave, settings):
    """Return one row for each approved current household member."""

    approved(settings)

    if not settings["current_codes"]:
        raise ValueError(f"{wave}: Current household member codes are missing.")

    data, _ = stata(wave, settings["file"])

    required = [
        settings["pid"],
        settings["household"],
        settings["membership"],
        settings["age"],
    ]
    require_columns(data, required, f"{wave} roster")

    # Remove former members using verified membership codes.
    current_codes = [str(code) for code in settings["current_codes"]]
    is_current = normalized(data[settings["membership"]]).isin(current_codes)
    data = data.loc[is_current].copy()

    roster = pd.DataFrame({
        "pidlink": normalized(data[settings["pid"]]),
        f"hhid_{wave}": normalized(data[settings["household"]]),
        f"age_{wave}": pd.to_numeric(data[settings["age"]], errors="coerce"),
    })

    roster = roster.dropna(subset=["pidlink", f"hhid_{wave}"])
    age = f"age_{wave}"
    roster.loc[~roster[age].between(0, 115), age] = np.nan

    # Do not silently remove duplicate PIDLINKs.
    assert_unique(roster, "pidlink", f"{wave} current roster")
    return roster


# ============================================================
# 2. ADD APPROVED IFLS3 BASELINE VARIABLES
# ============================================================

def add_baseline_covariates(baseline, variables):

    for variable in variables:
        approved(variable)

        name = variable["name"]
        level = variable["level"]

        if level == "person":
            merge_key = "pidlink"
        elif level == "household":
            merge_key = "hhid_ifls3"
        else:
            raise ValueError(f"{name}: Level must be person or household.")

        if name in baseline.columns:
            raise ValueError(f"Baseline variable already exists: {name}")

        data, _ = stata("ifls3", variable["file"])
        require_columns(
            data, [variable["key"], variable["variable"]], name
        )

        values = data[[variable["key"], variable["variable"]]].copy()
        values["merge_key"] = normalized(values[variable["key"]])
        values = values.dropna(subset=["merge_key"])

        method = variable.get("aggregation", "none")

        if method == "none":
            if values["merge_key"].duplicated().any():
                raise ValueError(
                    f"{name}: Multiple rows per {level}. "
                    "Specify an approved aggregation or use a unique file."
                )
            values = values[["merge_key", variable["variable"]]]

        elif method in ["sum", "mean", "min", "max"]:
            # Only numeric aggregates are allowed, after codebook approval.
            values["value"] = pd.to_numeric(
                values[variable["variable"]], errors="coerce"
            )

            if method == "sum":
                values = (
                    values.groupby("merge_key")["value"]
                    .sum(min_count=1)
                    .reset_index()
                )
            else:
                values = (
                    values.groupby("merge_key")["value"]
                    .agg(method)
                    .reset_index()
                )

            values = values.rename(columns={"value": variable["variable"]})
        else:
            raise ValueError(f"{name}: Unknown aggregation method {method}")

        values = values.rename(columns={
            "merge_key": merge_key,
            variable["variable"]: name,
        })
        baseline = baseline.merge(
            values[[merge_key, name]],
            on=merge_key,
            how="left",
            validate="many_to_one",
        )

    return baseline


# ============================================================
# 3. LOAD PREPARED IFLS4 BLT AND CES-D FILES
# ============================================================

def load_blt():
    """Read reviewed candidate treatment from 03a, without recoding KSR."""

    path = (
        "01_data/04_intermediate/rapsem_blt2005/"
        "blt2005_candidate_household_ifls4.csv"
    )
    blt = read_local_csv(path)

    require_columns(blt, ["hhid07", "blt_2005_06_candidate"], "03a BLT")
    blt["hhid_ifls4"] = normalized(blt["hhid07"])
    codes = normalized(blt["blt_2005_06_candidate"])

    invalid = codes.notna() & ~codes.isin(["0", "1"])
    if invalid.any():
        raise ValueError("03a BLT file contains a treatment code other than 0/1/NA.")

    blt["blt_2005"] = pd.to_numeric(codes, errors="coerce").astype("Int64")
    assert_unique(blt, "hhid_ifls4", "03a BLT households")

    return blt[["hhid_ifls4", "blt_2005"]]


def load_cesd():
    """Read the scored 03b indicators (KP01 skips already handled there)."""

    path = (
        "01_data/04_intermediate/rapsem_blt2005/"
        "cesd2007_candidate_items_wide.csv"
    )
    cesd = read_local_csv(path)
    items = [f"cesd_{letter}" for letter in "ABCDEFGHIJ"]

    require_columns(cesd, ["pidlink"] + items, "03b CES-D")
    cesd["pidlink"] = normalized(cesd["pidlink"])
    assert_unique(cesd, "pidlink", "03b CES-D respondents")

    for item in items:
        codes = normalized(cesd[item])
        invalid = codes.notna() & ~codes.isin(["0", "1", "2", "3"])
        if invalid.any():
            raise ValueError(f"03b CES-D item {item} contains an invalid score.")
        cesd[item] = pd.to_numeric(codes, errors="coerce").astype("Int64")

    # Recount observed items to avoid trusting an outdated saved count.
    cesd["cesd_observed_items"] = cesd[items].notna().sum(axis=1)
    cesd["cesd_complete_10"] = cesd["cesd_observed_items"].eq(10)

    return cesd[["pidlink"] + items + [
        "cesd_observed_items", "cesd_complete_10"
    ]]


# ============================================================
# 4. LOAD VERIFIED HOUSEHOLD WELFARE
# ============================================================

def load_welfare(settings):

    welfare = read_local_csv(settings["file"])

    required = [
        settings["wave_column"],
        settings["household_column"],
        settings["pce_column"],
        settings["poverty_line_column"],
    ]
    require_columns(welfare, required, "Harmonized welfare")

    welfare = welfare.rename(columns={
        settings["wave_column"]: "wave",
        settings["household_column"]: "hhid",
        settings["pce_column"]: "monthly_pce",
        settings["poverty_line_column"]: "poverty_line",
    })

    welfare["wave"] = normalized(welfare["wave"])
    welfare["hhid"] = normalized(welfare["hhid"])
    welfare["monthly_pce"] = pd.to_numeric(
        welfare["monthly_pce"], errors="coerce"
    )
    welfare["poverty_line"] = pd.to_numeric(
        welfare["poverty_line"], errors="coerce"
    )

    if (welfare["monthly_pce"].dropna() < 0).any():
        raise ValueError("Negative PCE values found.")
    if (welfare["poverty_line"].dropna() <= 0).any():
        raise ValueError("Poverty lines must be positive.")

    ratio = welfare["monthly_pce"] / welfare["poverty_line"]
    welfare["log_pce_pl"] = np.log(ratio.where(ratio > 0))
    welfare["poor"] = (
        welfare["log_pce_pl"].lt(0).astype("Int64")
        .where(welfare["log_pce_pl"].notna())
    )

    return welfare


# ============================================================
# 5. CONSTRUCT THE PERSON PANEL
# ============================================================

def main():

    config = read_config()

    for wave in ["ifls3", "ifls4", "ifls5"]:
        approved(config["rosters"][wave])
    approved(config["treatment"])
    approved(config["mediator"])
    approved(config["welfare"])

    if not config["treatment"].get("exposure_assignment_verified", False):
        raise ValueError(
            "Verify BLT 2005-06 historical household exposure and split-offs "
            "before building the person panel."
        )

    # Step 1. Start with IFLS3 baseline adults.
    baseline = load_roster("ifls3", config["rosters"]["ifls3"])
    minimum_age = int(config["analysis"].get("minimum_age_ifls3", 18))
    baseline = baseline.loc[baseline["age_ifls3"] >= minimum_age].copy()

    if baseline.empty:
        raise ValueError("No eligible IFLS3 baseline adults found.")

    baseline = add_baseline_covariates(
        baseline, config.get("baseline_covariates", [])
    )
    print(f"\nIFLS3 baseline adults: {len(baseline):,}")

    # Step 2. Link the same people to IFLS4 and IFLS5 by PIDLINK.
    ifls4 = load_roster("ifls4", config["rosters"]["ifls4"])
    ifls5 = load_roster("ifls5", config["rosters"]["ifls5"])

    panel = baseline.merge(
        ifls4, on="pidlink", how="left",
        validate="one_to_one", indicator="match_ifls4",
    )
    panel["observed_ifls4"] = panel["match_ifls4"].eq("both")
    panel = panel.drop(columns="match_ifls4")

    panel = panel.merge(
        ifls5, on="pidlink", how="left",
        validate="one_to_one", indicator="match_ifls5",
    )
    panel["observed_ifls5"] = panel["match_ifls5"].eq("both")
    panel = panel.drop(columns="match_ifls5")

    # Step 3. Add candidate BLT status using the IFLS4 household ID.
    blt = load_blt()
    panel = panel.merge(
        blt, on="hhid_ifls4", how="left", validate="many_to_one"
    )

    # Step 4. Add ten CES-D indicators using the individual ID.
    cesd = load_cesd()
    panel = panel.merge(
        cesd, on="pidlink", how="left", validate="one_to_one"
    )
    panel["observed_cesd"] = panel["cesd_observed_items"].fillna(0).gt(0)

    # Step 5. Merge household welfare separately for each wave.
    welfare = load_welfare(config["welfare"])

    for wave in ["ifls3", "ifls5"]:
        data = welfare.loc[
            welfare["wave"].eq(wave),
            ["hhid", "monthly_pce", "poverty_line", "log_pce_pl", "poor"],
        ].copy()

        if data.empty:
            raise ValueError(f"No welfare data available for {wave}.")

        assert_unique(data, "hhid", f"{wave} welfare")
        data = data.rename(columns={
            "hhid": f"hhid_{wave}",
            "monthly_pce": f"pce_{wave}",
            "poverty_line": f"pl_{wave}",
            "log_pce_pl": f"log_welfare_{wave}",
            "poor": f"poor_{wave}",
        })

        panel = panel.merge(
            data, on=f"hhid_{wave}", how="left", validate="many_to_one"
        )

    # Step 6. Describe poverty transitions and data availability.
    panel["baseline_poor"] = panel["poor_ifls3"].eq(1).fillna(False)

    panel["poverty_exit_2014"] = pd.Series(
        pd.NA, index=panel.index, dtype="Int64"
    )
    eligible = panel["baseline_poor"] & panel["poor_ifls5"].notna()
    panel.loc[eligible, "poverty_exit_2014"] = (
        1 - panel.loc[eligible, "poor_ifls5"]
    ).astype("Int64")

    panel["eligible_all_core"] = (
        panel["baseline_poor"]
        & panel["blt_2005"].notna()
        & panel["observed_cesd"]
        & panel["log_welfare_ifls5"].notna()
    )

    sample_flow = pd.DataFrame([
        ("IFLS3 baseline adults", len(panel)),
        ("Poor at baseline", int(panel["baseline_poor"].sum())),
        ("Linked to IFLS4", int(panel["observed_ifls4"].sum())),
        ("Linked to IFLS5", int(panel["observed_ifls5"].sum())),
        ("Candidate BLT status available", int(panel["blt_2005"].notna().sum())),
        ("At least one valid CES-D item", int(panel["observed_cesd"].sum())),
        ("All ten CES-D items", int(panel["cesd_complete_10"].fillna(False).sum())),
        ("Valid IFLS5 welfare", int(panel["log_welfare_ifls5"].notna().sum())),
        ("Baseline poor with all core variables", int(panel["eligible_all_core"].sum())),
    ], columns=["check", "n"])

    print("\n=== PANEL SAMPLE FLOW ===")
    print(sample_flow.to_string(index=False))

    # Step 7. Prepare files and check all paths before writing.
    output_files = {
        "baseline_person_2000.csv": baseline,
        "blt2005_household_ifls4.csv": blt,
        "cesd_items_2007.csv": cesd,
        "person_panel_full.csv": panel,
    }

    if config["analysis"].get("baseline_poor_only", True):
        analysis_panel = panel.loc[panel["baseline_poor"]].copy()
    else:
        analysis_panel = panel.copy()

    analysis_path = analysis_dir() / "baseline_poor_analysis_panel.csv"

    existing = [
        str(intermediate_dir() / name)
        for name in output_files
        if (intermediate_dir() / name).exists()
    ]
    if analysis_path.exists():
        existing.append(str(analysis_path))

    if existing:
        raise FileExistsError(
            "Previous private panel files exist. Back them up first:\n"
            + "\n".join(existing)
        )

    # The sample-flow report has no person or household identifiers.
    save_report(sample_flow, "04_panel_sample_flow.csv")

    for name, data in output_files.items():
        save_private(data, name)

    analysis_panel.to_csv(analysis_path, index=False)
    print("\nCreated private analysis panel:", analysis_path)
    print("STOP: This is a candidate panel, not a validated causal sample.")


if __name__ == "__main__":
    main()
