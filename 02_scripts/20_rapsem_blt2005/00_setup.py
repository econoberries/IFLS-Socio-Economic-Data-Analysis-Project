"""
00 — IFLS RAPSEM Project Setup

Purpose:
    1. Locate our existing IFLS project.
    2. Prepare folders for IFLS3, IFLS4, and IFLS5.
    3. Create documentation folders for each survey.
    4. Create folders for intermediate and analysis datasets.
    5. Create a folder for research output tables.

Notes:
    - Existing folders and files are never deleted or overwritten.
    - Original Stata (.dta) files remain untouched.
    - IFLS3 can be downloaded and added later.
"""

from common import project_root, REQUIRED, STUDY


# ============================================================
# 1. LOCATE OUR EXISTING IFLS PROJECT
# ============================================================

project_folder = project_root()

print("=" * 55)
print("IFLS RAPSEM PROJECT SETUP")
print("=" * 55)

print(f"\nProject folder: {project_folder}")


# ============================================================
# 2. PREPARE FOLDERS FOR THE ORIGINAL IFLS DATA
# ============================================================

raw_data_folder = project_folder / "01_data" / "01_raw_dta"

for wave in REQUIRED:

    for data_type in ["household", "community"]:

        folder = raw_data_folder / wave / data_type

        folder.mkdir(parents=True, exist_ok=True)

    print(f"Prepared raw data folders for {wave.upper()}")


# ============================================================
# 3. PREPARE SURVEY DOCUMENTATION FOLDERS
# ============================================================

documentation_folder = project_folder / "00_documentation"

document_types = [
    "codebooks",
    "questionnaires",
    "user_guides",
]

for wave in REQUIRED:

    for document_type in document_types:

        folder = documentation_folder / wave / document_type

        folder.mkdir(parents=True, exist_ok=True)

    print(f"Prepared documentation folders for {wave.upper()}")

# General documentation shared across surveys
(documentation_folder / "general").mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 4. PREPARE RESEARCH DATASET FOLDERS
# ============================================================

data_folder = project_folder / "01_data"

# Intermediate datasets: cleaned and merged data
intermediate_folder = data_folder / "04_intermediate" / STUDY

# Analysis datasets: final data used for estimation
analysis_folder = data_folder / "05_analysis" / STUDY

intermediate_folder.mkdir(parents=True, exist_ok=True)
analysis_folder.mkdir(parents=True, exist_ok=True)

print("\nPrepared research dataset folders.")


# ============================================================
# 5. PREPARE RESEARCH OUTPUT FOLDER
# ============================================================

output_folder = project_folder / "05_outputs" / "tables" / STUDY

output_folder.mkdir(parents=True, exist_ok=True)

print("Prepared research output folder.")


# ============================================================
# 6. PRINT FINAL SUMMARY
# ============================================================

print("\n" + "=" * 55)
print("PROJECT SETUP COMPLETED")
print("=" * 55)

print("\nRaw IFLS data:")
print(raw_data_folder)

print("\nDocumentation:")
print(documentation_folder)

print("\nIntermediate datasets:")
print(intermediate_folder)

print("\nAnalysis datasets:")
print(analysis_folder)

print("\nResearch output tables:")
print(output_folder)

print("\nExisting folders and original files were not modified.")

print("\nNext step:")
print("Run 01_inventory.py to inspect your available IFLS datasets.")
