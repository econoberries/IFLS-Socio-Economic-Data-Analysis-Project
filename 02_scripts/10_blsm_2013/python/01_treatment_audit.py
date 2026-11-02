"""01 — Audit IFLS5 BLSM codes, receipt status and reported payment dates.

Run from the IFLS project root:
    python 02_scripts/10_blsm_2013/python/01_treatment_audit.py

No causal treatment indicator is assigned in this script.
"""
import pandas as pd
from audit_common import (read_stata, code, key, year, labelled_codes,
                          variable_dictionary, save_aggregate, check_columns)

data, meta = read_stata("ifls5", "b1_ksr1")
needed = ["hhid14", "ksr3type", "ksr17", "ksr18y", "ksr18m", "ksr22y", "ksr22m"]
check_columns(data, needed, "IFLS5 b1_ksr1")
save_aggregate(variable_dictionary(meta, "ifls5", "b1_ksr1"),
               "01_transfer_dictionary.csv")

labels_by_var = meta.variable_value_labels or {}
for var in ["ksr3type", "ksr17", "ksr18y", "ksr22y"]:
    t = labelled_codes(data[var], labels_by_var.get(var))
    save_aggregate(t, f"01_{var}_frequencies.csv")
    if var in ["ksr3type", "ksr17"]:
        print(f"\n{var}\n{t.to_string(index=False)}")

# Questionnaire Book 1 KSR: BLSM is the KSR3TYPE column C.
# Never assume an unlabeled numeric value such as 3 means BLSM.
type_codes = data["ksr3type"].map(code).str.upper()
type_labels = {code(k): str(v).upper() for k, v
               in labels_by_var.get("ksr3type", {}).items()}
translated = type_codes.map(type_labels).fillna("")
select = type_codes.eq("C") | translated.str.contains(
    "BLSM|BANTUAN LANGSUNG SEMENTARA", regex=True
)
if not select.any():
    raise ValueError("Could not verify BLSM KSR3TYPE code. Inspect 01_ksr3type_frequencies.csv.")

blsm = data.loc[select].copy()
if key(blsm["hhid14"]).duplicated().any():
    raise ValueError("Repeated or missing BLSM household IDs: inspect source before coding.")
receipt = blsm["ksr17"].map(code)
first = year(blsm["ksr18y"])
last = year(blsm["ksr22y"])

classification = pd.Series("unknown_or_other", index=blsm.index)
classification.loc[receipt.eq("3")] = "reported_no"
classification.loc[receipt.eq("6")] = "no_program_code"
classification.loc[receipt.eq("1")] = "reported_yes_first_year_unknown"
classification.loc[receipt.eq("1") & first.eq(2013).fillna(False)] = "yes_first_2013"
classification.loc[receipt.eq("1") & first.lt(2013).fillna(False)] = "yes_first_before_2013"
classification.loc[receipt.eq("1") & first.gt(2013).fillna(False)] = "yes_first_after_2013"
save_aggregate(classification.value_counts().rename_axis("classification")
               .reset_index(name="n"), "01_blsm_timing_categories.csv")

timing = pd.DataFrame({
    "receipt_code": receipt,
    "first_year": first.astype("string").fillna("(unknown)"),
    "last_year": last.astype("string").fillna("(unknown)"),
    "classification": classification
})
save_aggregate(timing.value_counts(dropna=False).rename("n").reset_index(),
               "01_blsm_first_last_year_counts.csv")

bad_dates = (first.notna() & last.notna() & last.lt(first).fillna(False)).sum()
print(f"\nBLSM rows: {len(blsm):,}")
print(f"Reported yes, first receipt 2013: {(classification == 'yes_first_2013').sum():,}")
print(f"First/last year inconsistencies: {bad_dates:,}")
print("STOP: verify payment months and IFLS5 interview dates, ambiguous codes, "
      "and program-record coverage before defining treated and untreated households.")
