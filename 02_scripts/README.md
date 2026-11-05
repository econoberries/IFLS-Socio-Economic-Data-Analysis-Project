# Run order

Open `IFLS_Project.Rproj` and run these from the RStudio Console:

```r
source("02_scripts/00_setup_folders.R")
source("02_scripts/01_install_packages.R")
# Copy your extracted .dta datasets into 01_data/01_raw_dta before the next line.
source("02_scripts/02_convert_all_dta_to_csv.R")
```

`02a_convert_one_dta.R` is the helper loaded automatically by step 2.
`checks/check_conversion.R` is an optional synthetic converter check.
These scripts do not clear your R environment or change your working directory.


## New study audit: BLSM 2013, IFLS4–IFLS5

Use the standalone scripts in `02_scripts/10_blsm_2013/` after setting up the original IFLS4 and IFLS5 .dta files:

```r
source("02_scripts/10_blsm_2013/01_treatment_audit.R")
source("02_scripts/10_blsm_2013/02_panel_audit.R")
source("02_scripts/10_blsm_2013/03_welfare_inventory.R")
source("02_scripts/10_blsm_2013/04_interview_calendar_audit.R")
```

For explanations and output tables, see `03_notebooks/02_blsm_2013_ifls4_ifls5_audit.Rmd` and the [module instructions](10_blsm_2013/README.md). This is a variable/timing/eligibility **audit only**; it does not fit an ATT estimator, create a consumption aggregate, or write IFLS observations to GitHub.


### Python-first alternative (recommended for BLSM study)

The BLSM 2013 feasibility audit can now run **entirely in Python** without sourcing any R files. Open the project root, set up a Python virtual environment, then follow the [Python audit README](10_blsm_2013/python/README.md).

Run:

```bash
python 02_scripts/10_blsm_2013/python/01_treatment_audit.py
python 02_scripts/10_blsm_2013/python/02_panel_audit.py
python 02_scripts/10_blsm_2013/python/03_welfare_inventory.py
python 02_scripts/10_blsm_2013/python/04_interview_calendar_audit.py
```

A matching Jupyter notebook is available at [`03_notebooks/02_blsm_2013_ifls4_ifls5_audit_py.ipynb`](../03_notebooks/02_blsm_2013_ifls4_ifls5_audit_py.ipynb). No conversion to CSV is necessary: `pyreadstat` reads the original Stata files with value-label metadata. The earlier R scripts remain as optional references.


## RAPSEM BLT 2005–2006 Python preparation

See [20_rapsem_blt2005/README.md](20_rapsem_blt2005/README.md) for installation, source directory placement, variable code verification, and the conditional builder steps. From the directory containing \`IFLS_Project.Rproj\`:

\`\`\`bash
python -m pip install -r 02_scripts/20_rapsem_blt2005/requirements.txt
python 02_scripts/20_rapsem_blt2005/00_setup.py
python 02_scripts/20_rapsem_blt2005/01_inventory.py
python 02_scripts/20_rapsem_blt2005/02_candidate_audit.py
\`\`\`

Do not run welfare/panel builders until local, untracked \`study_config.json\` and \`welfare_basket.json\` are verified and approved.
