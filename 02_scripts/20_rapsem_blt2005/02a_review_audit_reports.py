"""
02a_review_audit_reports.py

Review reports already created by 01_inventory.py and 02_candidate_audit.py.
Only reads local aggregate CSV reports; does not read or alter raw data.

Run from the project root:
    python 02_scripts/20_rapsem_blt2005/02a_review_audit_reports.py
"""

import pandas as pd
from common import project_root


# 1. Locate previously generated audit reports.
REPORT_FOLDER = project_root() / "05_outputs" / "tables" / "rapsem_blt2005"


def read_report(filename, **kwargs):
    path = REPORT_FOLDER / filename
    if not path.is_file():
        raise SystemExit(
            f"Missing report: {path}\n"
            "Run 01_inventory.py and 02_candidate_audit.py first."
        )
    return pd.read_csv(path, **kwargs)


def main():
    print("\n=== 1. MISSING CANDIDATE DATASETS ===")
    checklist = read_report("01_study_module_checklist.csv")
    missing = checklist[
        ~checklist["available"].astype("string").str.lower().isin(
            ["true", "1", "yes"]
        )
    ]
    if missing.empty:
        print("All listed candidate file stems were found.")
    else:
        print(missing.to_string(index=False))
        print(
            "\nNote: A stem such as b3a_dl may be marked absent even when "
            "numbered files such as b3a_dl1.dta exist."
        )

    print("\n=== 2. CRITICAL FILE COUNTS ===")
    counts = read_report("02_critical_file_counts.csv")
    print(counts.to_string(index=False))

    print("\n=== 3. UNFILTERED PIDLINK OVERLAP ===")
    overlap = read_report("02_unfiltered_pidlink_overlap.csv")
    print(overlap.to_string(index=False))
    print(
        "These are shared IDs, NOT an analysis sample. "
        "Verify AR01A membership and duplicates before merging."
    )

    print("\n=== 4. IFLS4 KEY RESPONSE CODES ===")
    freq = read_report(
        "02_response_code_frequencies.csv",
        dtype={"code": "string"},
        keep_default_na=False,
    )
    wanted = {
        "ar01a", "ksr1type", "ksr2type", "ksr3type",
        "ksr17", "ksr18y", "ksr18m", "ksr22y", "ksr22m",
        "kptype", "kp01", "kp02",
    }
    selected = freq[
        (freq["wave"].astype("string").str.lower() == "ifls4")
        & (freq["variable"].astype("string").str.lower().isin(wanted))
    ]

    if selected.empty:
        print("No matching IFLS4 response frequencies were found.")
    else:
        for (file_name, variable), group in selected.groupby(
            ["file", "variable"], sort=True
        ):
            print(f"\n{file_name}: {variable}")
            top = group.sort_values("n", ascending=False).head(8)
            columns = ["code", "n"]
            if "label" in top.columns:
                columns.insert(1, "label")
            print(top[columns].to_string(index=False))

    print("\nReview complete. No source datasets were modified.")


if __name__ == "__main__":
    main()
