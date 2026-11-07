"""
01 — IFLS Data Inventory

Purpose:
    1. Find all Stata (.dta) files in IFLS3, IFLS4, and IFLS5.
    2. Record basic information about each dataset.
    3. Collect all variable names and labels.
    4. Identify variables potentially relevant to our research.
    5. Check whether the candidate research datasets are available.

Notes:
    - Reads Stata metadata only, not individual observations.
    - Does not modify the original datasets.
    - A survey wave can be added later.
"""


# ============================================================
# 1. IMPORT PACKAGES AND PROJECT SETTINGS
# ============================================================

import re

import pandas as pd
import pyreadstat

from common import REQUIRED, STEMS, source_root, find_dta, save_report


# Folder containing the original Stata files
raw_folder = source_root()

# Keywords related to our RAPSEM research
keywords = [
    "cash", "transfer", "blt", "benefit",
    "poverty", "poor", "food", "consum", "expend",
    "salary", "wage", "income", "asset",
    "health", "depress", "stress",
    "educat", "school", "work", "labor", "employment",
    "household", "interview", "member",
    "province", "urban", "rural", "year",
]

keyword_pattern = re.compile("|".join(keywords), re.IGNORECASE)

# Lists to store the inventory results
file_inventory = []
variable_dictionary = []
research_candidates = []


# ============================================================
# 2. FIND AND INSPECT ALL STATA DATASETS
# ============================================================

for wave in REQUIRED:

    wave_folder = raw_folder / wave

    print(f"\nChecking {wave.upper()}...")

    # A wave may not have been downloaded yet.
    if not wave_folder.exists():
        print(f"Folder not found: {wave_folder}")
        continue

    # Search all subfolders, including extracted household folders.
    stata_files = sorted(
        file
        for file in wave_folder.rglob("*")
        if file.is_file() and file.suffix.lower() == ".dta"
    )

    print(f"Found {len(stata_files)} Stata files.")

    # --------------------------------------------------------
    # 3. READ METADATA FROM EACH DATASET
    # --------------------------------------------------------

    for file in stata_files:

        print(f"  Reading: {file.name}")

        relative_path = str(file.relative_to(raw_folder))

        try:
            # Read metadata only, not survey observations.
            _, metadata = pyreadstat.read_dta(
                str(file),
                metadataonly=True,
                apply_value_formats=False,
            )

            # Record basic dataset information.
            file_inventory.append({
                "wave": wave,
                "relative_path": relative_path,
                "stem": file.stem,
                "rows": metadata.number_rows,
                "columns": len(metadata.column_names),
                "status": "OK",
            })

            # ------------------------------------------------
            # 4. COLLECT VARIABLE NAMES AND LABELS
            # ------------------------------------------------

            labels = metadata.column_names_to_labels or {}

            for variable in metadata.column_names:

                label = labels.get(variable) or ""

                variable_info = {
                    "wave": wave,
                    "stem": file.stem,
                    "variable": variable,
                    "label": label,
                }

                # Complete variable dictionary
                variable_dictionary.append(variable_info)

                # Flag variables potentially relevant to our research.
                search_text = f"{variable} {label}"

                if keyword_pattern.search(search_text):
                    research_candidates.append(variable_info)

        except Exception as error:

            # Record files that could not be inspected.
            file_inventory.append({
                "wave": wave,
                "relative_path": relative_path,
                "stem": file.stem,
                "rows": None,
                "columns": None,
                "status": (
                    f"ERROR {type(error).__name__}: "
                    f"{str(error)[:150]}"
                ),
            })

            print(f"  Could not read {file.name}: {error}")


# ============================================================
# 5. SAVE THE INVENTORY AND VARIABLE DICTIONARIES
# ============================================================

save_report(
    pd.DataFrame(
        file_inventory,
        columns=["wave", "relative_path", "stem", "rows", "columns", "status"],
    ),
    "01_file_inventory.csv",
)

save_report(
    pd.DataFrame(
        variable_dictionary,
        columns=["wave", "stem", "variable", "label"],
    ),
    "01_all_variable_dictionary.csv",
)

save_report(
    pd.DataFrame(
        research_candidates,
        columns=["wave", "stem", "variable", "label"],
    ),
    "01_research_variable_candidates.csv",
)


# ============================================================
# 6. CHECK CANDIDATE DATASETS FOR OUR RAPSEM STUDY
# ============================================================

module_checklist = []

for wave in REQUIRED:

    for dataset in STEMS[wave]:

        # Find the dataset anywhere within the wave folder.
        file = find_dta(wave, dataset, required=False)

        module_checklist.append({
            "wave": wave,
            "stem": dataset,
            "available": file is not None,
        })

save_report(
    pd.DataFrame(
        module_checklist,
        columns=["wave", "stem", "available"],
    ),
    "01_study_module_checklist.csv",
)


# ============================================================
# 7. PRINT FINAL SUMMARY
# ============================================================

print("\n" + "=" * 55)
print("IFLS DATA INVENTORY COMPLETED")
print("=" * 55)

print(f"Datasets inspected: {len(file_inventory):,}")
print(f"Variables recorded: {len(variable_dictionary):,}")
print(f"Research candidates: {len(research_candidates):,}")

missing = sum(
    not item["available"]
    for item in module_checklist
)

print(f"Candidate modules not found: {missing:,}")

print("\nReports saved to:")
print("05_outputs/tables/rapsem_blt2005/")

print("\nNext step:")
print("Review the module checklist and variable dictionaries.")
print("Then run 02_candidate_audit.py.")

print(
    "\nNote: A missing dataset may be unavailable, differently "
    "named, or not needed for our study."
)
