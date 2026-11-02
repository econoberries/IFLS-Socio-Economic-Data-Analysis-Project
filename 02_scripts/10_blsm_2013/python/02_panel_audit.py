"""02 — Audit IFLS4–IFLS5 person and household tracking (aggregate only).

Run:
    python 02_scripts/10_blsm_2013/python/02_panel_audit.py

PIDLINK is a person identifier; do not equate household IDs across waves.
This audits presence and uniqueness, without silently constructing a panel.
"""
import pandas as pd
from audit_common import (find_dta, read_stata, key, save_aggregate,
                          variable_dictionary)

results = []
rosters = {}
for wave, hhid in [("ifls4", "hhid07"), ("ifls5", "hhid14")]:
    df, meta = read_stata(wave, "bk_ar1")
    save_aggregate(variable_dictionary(meta, wave, "bk_ar1"),
                   f"02_roster_{wave}_dictionary.csv")
    if "pidlink" not in df.columns:
        results.append({"wave": wave, "measure": "missing_pidlink", "n": len(df)})
        continue
    ids = key(df["pidlink"])
    rosters[wave] = set(ids.dropna())
    results += [
        {"wave": wave, "measure": "roster_rows", "n": len(df)},
        {"wave": wave, "measure": "nonmissing_pidlink", "n": int(ids.notna().sum())},
        {"wave": wave, "measure": "unique_pidlink", "n": len(rosters[wave])},
        {"wave": wave, "measure": "repeated_pidlink_rows",
         "n": int(ids[ids.notna()].duplicated().sum())},
    ]
    if hhid in df.columns:
        hh = key(df[hhid])
        results.append({"wave": wave, "measure": "unique_household_ids",
                        "n": int(hh.dropna().nunique())})
    else:
        results.append({"wave": wave, "measure": f"missing_{hhid}", "n": len(df)})

if len(rosters) == 2:
    results.append({
        "wave": "both", "measure": "pidlink_intersection_unfiltered",
        "n": len(rosters["ifls4"] & rosters["ifls5"])
    })
save_aggregate(pd.DataFrame(results), "02_roster_linkage_counts.csv")

# Inspect tracking records without assuming specific member/result field names.
for stem in ["ptrack", "ptrack14", "htrack", "htrack14"]:
    path = find_dta("ifls5", stem, required=False)
    if path is None:
        continue
    frame, meta = read_stata("ifls5", stem)
    save_aggregate(variable_dictionary(meta, "ifls5", stem),
                   f"02_{stem}_dictionary.csv")
    summary = [{"field": "rows", "n": len(frame)}]
    for field in ["pidlink", "hhid07", "hhid14"]:
        if field in frame.columns:
            s = key(frame[field])
            summary += [
                {"field": f"{field}_nonmissing", "n": int(s.notna().sum())},
                {"field": f"{field}_unique", "n": int(s.dropna().nunique())},
            ]
    if all(x in frame.columns for x in ["hhid07", "hhid14"]):
        pairs = pd.DataFrame({
            "base": key(frame["hhid07"]),
            "follow": key(frame["hhid14"])
        }).dropna().drop_duplicates()
        n_destinations = pairs.groupby("base")["follow"].nunique()
        split_summary = n_destinations.value_counts().rename_axis(
            "distinct_followup_households").reset_index(name="baseline_households")
        save_aggregate(split_summary, f"02_{stem}_splitoff_counts.csv")
        summary.append({"field": "distinct_complete_household_pairs",
                        "n": len(pairs)})
    save_aggregate(pd.DataFrame(summary), f"02_{stem}_tracking_counts.csv")

print("Panel audit complete. Check tracking variable labels and roster membership "
      "codes. Overlap of PIDLINKs alone does NOT define the final eligible sample.")
