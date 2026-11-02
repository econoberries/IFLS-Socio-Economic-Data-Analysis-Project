"""04 — Locate interview-date variables in IFLS4 and IFLS5 metadata.

Run:
    python 02_scripts/10_blsm_2013/python/04_interview_calendar_audit.py

No interview dates or exposure timing are guessed from variable names.
"""
import re
import pandas as pd
from audit_common import find_dta, read_stata, variable_dictionary, save_aggregate

files = ["b1_time", "bk_time", "b1_cov", "bk_cov"]
pattern = re.compile(
    r"interview|interviewer|date|month|year|tanggal|bulan|tahun|^time",
    re.IGNORECASE
)
source_summary = []
candidate_tables = []

for wave in ("ifls4", "ifls5"):
    for stem in files:
        found = find_dta(wave, stem, required=False)
        source_summary.append({"wave": wave, "file": stem,
                               "present": found is not None})
        if found is None:
            continue
        _, meta = read_stata(wave, stem, metadata_only=True)
        dictionary = variable_dictionary(meta, wave, stem)
        matches = dictionary.apply(
            lambda row: bool(pattern.search(row["variable"]) or
                             pattern.search(row["description"])),
            axis=1
        )
        candidate_tables.append(dictionary.loc[matches])

save_aggregate(pd.DataFrame(source_summary), "04_interview_source_inventory.csv")
if candidate_tables:
    candidates = pd.concat(candidate_tables, ignore_index=True)
    save_aggregate(candidates, "04_interview_variable_candidates.csv")
    print(candidates.to_string(index=False))
else:
    print("No interview-date candidates identified. Review IFLS4/5 cover "
          "questionnaires and tracking files manually.")

print("Next step: verify date formats and compare 2013 BLSM payment dates "
      "to actual IFLS5 interviews, including late-2014 transfer exposure.")
