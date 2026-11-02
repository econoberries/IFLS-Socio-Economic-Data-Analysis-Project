"""03 — Inventory welfare-related IFLS4 and IFLS5 expenditure files.

Run:
    python 02_scripts/10_blsm_2013/python/03_welfare_inventory.py

Metadata-only: no household consumption total is constructed yet.
"""
import pandas as pd
from audit_common import find_dta, read_stata, variable_dictionary, save_aggregate

# KS reference periods, category definitions, annualization, housing,
# self-consumption and deflators must be verified from the questionnaires.
candidates = [
    "b1_ks0", "b1_ks1", "b1_ks2", "b1_ks3", "b1_ks4",
    "b2_kr", "bk_ar1", "b1_cov"
]
summary = []
dictionaries = []

for wave in ("ifls4", "ifls5"):
    for stem in candidates:
        found = find_dta(wave, stem, required=False)
        if found is None:
            summary.append({"wave": wave, "file": stem, "exists": False,
                            "rows": pd.NA, "columns": pd.NA})
            continue
        df, meta = read_stata(wave, stem, metadata_only=True)
        summary.append({
            "wave": wave, "file": stem, "exists": True,
            "rows": getattr(meta, "number_rows", None),
            "columns": len(meta.column_names)
        })
        dictionaries.append(variable_dictionary(meta, wave, stem))

save_aggregate(pd.DataFrame(summary), "03_welfare_file_inventory.csv")
if dictionaries:
    save_aggregate(pd.concat(dictionaries, ignore_index=True),
                   "03_welfare_variable_dictionary.csv")

print("Welfare metadata inventory complete.")
print("BEFORE constructing monthly consumption: verify KS item reference periods, "
      "food and nonfood coverage, housing and own production, special values, "
      "current household size, inflation, spatial prices, and double counting.")
print("A cash transfer received is NOT itself a consumption expenditure.")
