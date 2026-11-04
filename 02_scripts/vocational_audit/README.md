# IFLS vocational education cohort feasibility audit

Run from the project root in RStudio. Scripts do not modify raw files.

1. Run `source("02_scripts/vocational_audit/01_inventory_files.R")`.
2. Inspect `01_inventory_files.csv`; edit `roster4_file` and `roster5_file` in `00_audit_setup.R` using exact relative paths.
3. Run `02_inspect_roster.R` and review identifier/age dictionaries and duplicate diagnostics.
4. Only when IDs are verified unique and age variables checked, run `03_link_cohorts.R`. If duplicates exist, stop and develop an explicit record-resolution rule from IFLS documentation.
5. Run `04_discover_outcome_files.R` to produce candidate variable inventory. Verify variables with the IFLS questionnaires/codebooks before constructing SMK/SMA and outcomes.

**Important:** CSV exports can lose Stata variable/value labels and missing-value metadata. Verify coding against the original `.dta` files or official codebooks. `pidlink`, `ar09`, and filename patterns are candidates requiring verification, not guaranteed cross-wave schema. No treatment/outcome effects are estimated in this audit.
