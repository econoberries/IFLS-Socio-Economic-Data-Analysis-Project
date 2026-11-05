# IFLS Socio-Economic Data Analysis Project

Owner: Khaira Abdillah

A fresh, reproducible R workspace for organizing IFLS source data and documentation,
creating CSV copies, and building education and socioeconomic analyses.

## Start here

Your current local project folder is:

```text
/Users/khaira_abdillah/Documents/IFLS_Causal_Project/IFLS-Socio-Economic-Data-Analysis-Project-main/
```

1. Open **IFLS_Project.Rproj** inside this folder in RStudio.
2. Open **00_master_setup.Rmd**, which belongs directly in the project root.
3. Click **Knit** to install missing packages, prepare folders, list source files,
   and run the synthetic converter check. If R Markdown is not yet installed,
   run `source("02_scripts/01_install_packages.R")` in the Console first.
4. Inspect the file inventory and check that your source datasets are present.
5. In the master document's settings chunk, change
   `convert_dta_to_csv <- FALSE` to `convert_dta_to_csv <- TRUE` and knit again
   when ready to create CSV copies.

The master document calls the existing R scripts in order. It uses your actual
project path, which you can edit in its settings chunk if the folder moves.
You can also run the chunks in order while the correct RStudio project is open.
Full conversion is off by default, and the overwrite setting in `config.R`
remains `FALSE`.

You can start with IFLS4 alone, including your existing source file at
`01_data/01_raw_dta/ifls4/household/hh07_all_dta/b1_cov.dta`.
Its CSV copy will be placed at
`01_data/02_raw_csv/ifls4/household/hh07_all_dta/b1_cov.csv`.
Empty folders for other surveys do not prevent conversion. No source IFLS
datasets are included in the repository.

For the individual Console commands instead, see [02_scripts/README.md](02_scripts/README.md).

## Main folders

| Folder | What belongs here | GitHub |
| --- | --- | --- |
| `00_documentation/` | Downloaded questionnaires, codebooks, user guides, literature, and a source register | Instructions and source register only |
| `01_data/` | Original Stata files, CSV copies, metadata, and later derived datasets | Folder placeholders and instructions only |
| `02_scripts/` | Reusable R scripts for setup, conversion, and later data construction | Tracked |
| `03_notebooks/` | R Markdown explanations, source inventories, and exploration | Source `.Rmd` files tracked |
| `04_notes/` | Research questions, variable decisions, and meeting notes | Tracked |
| `05_outputs/` | Generated tables, figures, and run logs | Instructions and placeholders only |
| `06_paper/` | Seminar paper source and references | Tracked |
| `config.R` | Project paths and conversion settings | Tracked |

Downloaded documents and data stay on your computer even though the repository is
private. `.gitignore` prevents these files from being added by ordinary Git commands.
Keep a separate backup of your local data and documents; GitHub does not back them up.

## Where to put the original datasets

Separate each survey, then household and community data:

| Survey folder | Original household files | Original community files |
| --- | --- | --- |
| `ifls1` | `01_data/01_raw_dta/ifls1/household/` | `01_data/01_raw_dta/ifls1/community/` |
| `ifls2` | `01_data/01_raw_dta/ifls2/household/` | `01_data/01_raw_dta/ifls2/community/` |
| `ifls3` | `01_data/01_raw_dta/ifls3/household/` | `01_data/01_raw_dta/ifls3/community/` |
| `ifls4` | `01_data/01_raw_dta/ifls4/household/` | `01_data/01_raw_dta/ifls4/community/` |
| `ifls5` | `01_data/01_raw_dta/ifls5/household/` | `01_data/01_raw_dta/ifls5/community/` |

The setup script also creates separate `ifls2plus` and `ifls_east` folders. Keep
these surveys separate; folder organization does not establish panel comparability.

For example, put `bk_ar1.dta` in
`01_data/01_raw_dta/ifls5/household/bk_ar1.dta`.
If you keep an extracted `hh14_all_dta` subfolder instead, that is fine: the
converter searches recursively and reproduces that extra subfolder in its output.

Do not clean or overwrite files in `01_raw_dta`. Build derived datasets in the
intermediate and analysis folders. Do not combine files from different waves into
one source folder, since many have the same names.

## Where to put questionnaires and other documentation

For each survey, use these folders. Replace `ifls5` with the relevant survey:

| Document | Location |
| --- | --- |
| Household and community questionnaires | `00_documentation/ifls5/questionnaires/` |
| Codebooks, variable lists, and data dictionaries | `00_documentation/ifls5/codebooks/` |
| User guides, fieldwork reports, sampling and weighting notes | `00_documentation/ifls5/user_guides/` |
| Documentation covering multiple surveys | `00_documentation/general/` |
| Research articles | `00_documentation/literature/` |

Preserve the original downloaded filenames. If useful, add `household` and
`community` subfolders under `questionnaires`. Record download URLs and dates in
`00_documentation/source_register.csv`.

## What the conversion creates

| Data stage | Purpose | Example |
| --- | --- | --- |
| `01_raw_dta` | Untouched, authoritative Stata source | `ifls5/household/bk_ar1.dta` |
| `02_raw_csv` | Uncleaned CSV copy of each source dataset | `ifls5/household/bk_ar1.csv` |
| `03_metadata` | Companion labels, types, missing tags, and source information | `ifls5/household/bk_ar1__variables.csv` |
| `04_intermediate` | Later reshaping, harmonization, and merge steps | Nothing created yet |
| `05_analysis` | Later final analysis samples | Nothing created yet |

For every dataset, the converter writes one UTF-8 CSV plus four metadata files:

- `__variables.csv`: variable order, variable labels, R classes, storage types,
  and Stata display formats available through haven.
- `__value_labels.csv`: response codes and their labels, including labelled
  missing codes when present.
- `__tagged_missing.csv`: the variable, original one-based row number, and tag
  for each `.a`, `.b`, etc. missing value. A header-only file means no tags occurred.
- `__file_info.csv`: relative source path, MD5 checksum, dimensions, dataset label,
  conversion time, and package versions.

The main CSV preserves variable names, column order, row order, numeric response
codes, and string values. Nothing is filtered, merged, or substantively recoded.
CSV is a derived exchange format, not a complete Stata replacement:

- Variable/value labels and tagged missing distinctions live in the metadata files.
- Numeric missing values are blank CSV fields. Empty Stata strings also remain blank.
- Dates and times imported by haven use readable date/time representations;
  CSV does not retain Stata's numeric date encoding or display format.
- Other Stata features not exposed by haven, such as some notes and characteristics,
  may not be exported. Always retain the `.dta` files.
- CSV has no column types. When importing it later, explicitly set identifier columns
  to character so leading zeros survive. Excel's automatic conversions can change IDs.

Numeric special response codes such as `8`, `9`, or `900` remain numeric codes;
this step does not decide which codes should be treated as missing in an analysis.
For work in R, reading the original `.dta` with `haven::read_dta()` is often the
most convenient way to retain labels.

## Selecting surveys and repeating a conversion

Choose the surveys at the top of `02_scripts/02_convert_all_dta_to_csv.R`.
This setting is used whether you run the script directly or through the master Rmd.

To check every survey currently in the raw-data folder:

```r
surveys_to_convert <- "all"
```

After completing IFLS4 and IFLS5, you can add earlier waves and select only those:

```r
surveys_to_convert <- c("ifls1", "ifls2", "ifls3")
```

With that selection, IFLS4 and IFLS5 are excluded from processing. To process just
one survey, use `surveys_to_convert <- "ifls3"`. If a selected survey has no source
files yet, the script reports that; other selected surveys with data can still run.

Before processing, the script displays the selected surveys, counts by survey and
component, and overwrite mode. Every progress line shows the relative source path,
including its survey folder. The progress counter counts files checked, not files
newly converted. The result of each check is explicitly labelled:

| Result | Meaning |
| --- | --- |
| `CONVERTED` | CSV and companion metadata were written |
| `SKIPPED` | A complete export exists and the source checksum matches; outputs were not rewritten |
| `FAILED` | An error occurred; read the printed explanation or saved inventory |

Keep `overwrite_csv <- FALSE` in `config.R` for routine work. With that setting,
selecting `"all"` checks existing exports but does not recreate complete exports
whose source checksums match. A new source file is converted. An incomplete export
or changed source is reported as a failure rather than silently overwritten.

To deliberately recreate exports, select the intended surveys, set
`overwrite_csv <- TRUE`, run the conversion, then set it back to `FALSE`.
Existing CSV contents are not checksummed; this option can repair an export you
have edited. Treat `02_raw_csv` as read-only. The script does not remove orphaned
exports when a source is renamed or removed.

Each run prints converted, skipped, and failed counts by survey and saves a status
inventory and R session information in `05_outputs/logs/`. The inventory includes
survey and component columns. One failed file does not prevent the remaining
selected source files from being attempted. Run only one conversion process at a
time, including conversions started from the terminal, RStudio, or the master Rmd.

## Optional notebook and converter check

After package installation, open `03_notebooks/01_start_here.Rmd` and click **Knit**
using RStudio's default document-directory knit setting. It creates folders and
lists source files; it does not run a full conversion.

To check the converter with synthetic data on your computer:

```r
source("02_scripts/checks/check_conversion.R")
```

This check uses a temporary directory, including labelled values, tagged missings,
dates, nested paths, leading-zero IDs, repeated runs, and changed sources. It does
not read or modify your IFLS data.

## Technical references

- [haven: reading Stata files and imported labels](https://haven.tidyverse.org/reference/read_dta.html)
- [haven: tagged missing values](https://haven.tidyverse.org/reference/tagged_na.html)
- [readr: writing CSV files](https://readr.tidyverse.org/reference/write_delim.html)


## New study module: RAPSEM mediation of BLT 2005–2006

The Python-first **BLT 2005–2006 → CES-D distress (IFLS4) → household welfare (IFLS5)** preparation workflow is maintained separately from the BLSM 2013 study.

- **Full instructions:** [02_scripts/20_rapsem_blt2005/README.md](02_scripts/20_rapsem_blt2005/README.md).
- **Data:** download IFLS3 (2000), IFLS4 (2007–08), and IFLS5 (2014–15) Stata household files; place each in its own `01_data/01_raw_dta/iflsN/household/` directory.
- **Python setup:** use Python 3.12 in a project `.venv`, then install `02_scripts/20_rapsem_blt2005/requirements.txt`; complete commands are in the [study README](02_scripts/20_rapsem_blt2005/README.md).
- **Start:** run `00_setup.py`, `01_inventory.py`, `02_candidate_audit.py`, then reusable reviews `02a_review_audit_reports.py`, `02b_focused_code_audit.py`, and `02c_measurement_validation.py`.
- **Do not run the builders yet:** treatment receipt codes, roster membership codes, CES-D item codes, and poverty lines require verification first.
- **Privacy:** no raw observations, local configuration files, or analysis panels are committed to GitHub.

**Identification warning:** the published RAPSEM R estimator assumes randomized treatment; observational BLT mediation requires a separate identification argument and validated extension. This module prepares data only; it does **not** estimate ATT or causal mediation effects.
