# RAPSEM–IFLS: from downloaded data to validated analysis panel

**Research topic:** BLT 2005–2006 → psychological distress in IFLS4 → household welfare / poverty exit in IFLS5, using IFLS3 as the pretreatment baseline.  This is a **data-preparation workflow**, not a causal estimator. It does not calculate ATT, propensity scores, CFA, or RAPSEM coefficients.

**Important distinction:** the original RAPSEM R code is designed for randomized treatment. Our observational adaptation must be separately validated after data preparation. The data pipeline never assumes that matching or weighting makes RAPSEM automatically valid.

## 0. Locate the project root; do not make a second IFLS project

Use the existing directory containing `IFLS_Project.Rproj`. Depending on your local checkout it can be either

```text
/Users/khaira_abdillah/Documents/IFLS_Causal_Project/
```

or

```text
/Users/khaira_abdillah/Documents/IFLS_Causal_Project/IFLS-Socio-Economic-Data-Analysis-Project-main/
```

The important test is that `IFLS_Project.Rproj`, `01_data/`, and `02_scripts/` are all in the same directory. The new scripts find this root automatically. From Terminal, do:

```bash
cd "/Users/khaira_abdillah/Documents/IFLS_Causal_Project"
ls IFLS_Project.Rproj
```

If the second command says the file does not exist, `cd` into the nested repository directory instead and run it again.

### Installed as part of the GitHub repository

After cloning or pulling this repository, the RAPSEM study scripts are already present. No separate starter ZIP is required. The module contains:

```text
RAPSEM_SETUP_README.md
02_scripts/20_rapsem_blt2005/
    common.py
    00_setup.py
    01_inventory.py
    02_candidate_audit.py
    02a_review_audit_reports.py
    02b_focused_code_audit.py
    02c_measurement_validation.py
    03a_build_blt_treatment.py
    03b_build_cesd_indicators.py
    measurement_rules_ifls4.md
    tests/test_candidate_measurement.py
    03_build_welfare.py
    04_build_panel.py
    05_quality_report.py
    study_config.example.json
    welfare_basket.example.json
    requirements.txt
00_documentation/general/poverty_lines_household.template.csv
```

Existing `02_scripts/10_blsm_2013/` and IFLS conversion scripts are left untouched.

## 1. Prepare Python (Mac Terminal)

Install **Python 3.12** from [python.org](https://www.python.org/downloads/) first, if needed. Do not replace the Python version managed by macOS. Run from the project root (the directory containing `IFLS_Project.Rproj`):

```bash
# First-time setup (create .venv only once).
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r 02_scripts/20_rapsem_blt2005/requirements.txt
python 02_scripts/20_rapsem_blt2005/00_setup.py
```

**On future visits**, do not recreate `.venv` or reinstall everything. From the project root, run `source .venv/bin/activate`, verify `python --version`, and run the relevant audit script. Use `deactivate` when finished. On this Mac, unqualified `python3` may refer to the older system Python 3.9; use `python3.12` for creating the virtual environment.

`00_setup.py` creates missing directories only. It **never** moves or overwrites raw data.

## 2. Put each downloaded IFLS wave in the correct folder

Use the public-use `.dta` (Stata) files from RAND. Register and follow RAND's terms of access if necessary: https://www.rand.org/well-being/social-and-behavioral-policy/data/FLS/IFLS/access.html . Download the following household components and documentation:

| Wave | Download | Put extracted `.dta` files under | Put guide/codebook/questionnaire under |
|---|---|---|---|
| IFLS3 / 2000 | Household Stata data (`hh00_all_dta`) | `01_data/01_raw_dta/ifls3/household/` | `00_documentation/ifls3/` |
| IFLS4 / 2007–08 | Household Stata data (`hh07_all_dta`) | `01_data/01_raw_dta/ifls4/household/` | `00_documentation/ifls4/` |
| IFLS5 / 2014–15 | Household Stata data (`hh14_all_dta`) | `01_data/01_raw_dta/ifls5/household/` | `00_documentation/ifls5/` |

You may retain subfolders like `hh07_all_dta/` inside each `household/` folder; the scripts search recursively. **Do not** place the same file in two locations within one wave, or the code intentionally stops to avoid ambiguous inputs. Do not rename questionnaire variables or modify any source `.dta` file. The existing `01_data/02_raw_csv/` mirror is optional and is not used by these Python scripts.

Community-facility data are optional for the initial dataset. If we decide to add village characteristics, put them in the matching wave's `community/` folder; never mingle household and community extracts.

### Modules the research will draw on

| What we need | Wave | Candidate module/files | Data level |
|---|---|---|---|
| Household roster, membership, person and household IDs | IFLS3, IFLS4, IFLS5 | `bk_ar1`; also examine `bk_ar0` and tracking files | Person / household |
| BLT I 2005–06 historical receipt | IFLS4 | **Audit** `b1_ksr1`, `b1_ksr3`, `b1_ksr4` and possibly `b2_kr` | Household / program record |
| CES-D-10 distress indicator responses | IFLS4 | `b3b_kp` | Person × item |
| Expenditure for baseline and outcome | IFLS3, IFLS5 | `b1_ks0`, `b1_ks1`, `b1_ks2`, `b1_ks3` | Household / item |
| Baseline demographics | IFLS3 | `bk_ar1` | Person |
| Baseline schooling, work, health, housing, assets | IFLS3 | `b3a_dl*`, `b3a_tk*`, `b3b_kk*`, `b2_kr*`, `b2_hr*`, etc. | Mixed; verify uniqueness |
| Later transfers, jobs, migration, health changes | IFLS4/5 | `b1_ksr*`, `b3a_tk*`, `b3a_mg*`, `b3b_kk*` | Diagnostics only; not automatic controls |

A module marked with `*` may have several differently numbered data files. The **metadata audit**, not this table, determines which actually exist and their exact fields.

## 3. Audit all the downloaded variables (no coding decisions yet)

```bash
python 02_scripts/20_rapsem_blt2005/01_inventory.py
python 02_scripts/20_rapsem_blt2005/02_candidate_audit.py
python 02_scripts/20_rapsem_blt2005/02a_review_audit_reports.py
python 02_scripts/20_rapsem_blt2005/02b_focused_code_audit.py
python 02_scripts/20_rapsem_blt2005/02c_measurement_validation.py
```

The two extra, **re-runnable** checks are:

- `02a_review_audit_reports.py`: summarizes the existing inventory, candidate file counts, unfiltered PIDLINK overlap and key response-code frequencies. It requires the earlier two reports and writes no new files.
- `02b_focused_code_audit.py`: reads IFLS4 `b1_ksr1.dta` and `b3b_kp.dta` without changing them, displays treatment/mediator code cross-tabs and KP02 missingness, and writes only aggregate CSV tables named `02b_*.csv` to `05_outputs/tables/rapsem_blt2005/`. If `KP01` is absent, it reports that fact instead of inferring a screening mechanism.
- `02c_measurement_validation.py`: checks whether IFLS4 cash-transfer records are unique at the HHID07 × program level, compares reported receipt years, audits unique A–J CES-D item rows per PIDLINK, and summarizes the KP01/KP02 response pattern. Writes aggregate-only `02c_*.csv` reports and a checklist of questionnaire decisions **not yet verified**. It neither assigns treatment nor constructs CES-D scores.

Examine these reports in `05_outputs/tables/rapsem_blt2005/`:

1. `01_study_module_checklist.csv`: missing/existing candidate files by wave.
2. `01_all_variable_dictionary.csv`: **every variable** in every local Stata file, its wave and label.
3. `01_research_variable_candidates.csv`: broad keyword shortlist, useful for the research variable audit.
4. `02_response_code_frequencies.csv`: observed `KSR*`, `KPTYPE`, `KP02`, `AR01A` codes and sample counts (aggregated only).
5. `02_unfiltered_pidlink_overlap.csv`: raw ID overlap **not** the final eligible sample.

### 3A. Build **provisional**, separately audited IFLS4 measures

After reviewing Book 1 Section KSR (p. 9), Book 3B Section KP (p. 12),
and the special-code rules in the IFLS4 User's Guide Volume 2, run:

\`\`\`bash
# Aggregates only (safe to re-run; source .dta files are unchanged).
python 02_scripts/20_rapsem_blt2005/03a_build_blt_treatment.py
python 02_scripts/20_rapsem_blt2005/03b_build_cesd_indicators.py

# Test the candidate coding functions on synthetic responses (no IFLS data).
python -m pytest 02_scripts/20_rapsem_blt2005/tests/test_candidate_measurement.py -q
\`\`\`

These two scripts generate \`03a_*.csv\` and \`03b_*.csv\` aggregate tables in
\`05_outputs/tables/rapsem_blt2005/\`. The first script distinguishes confirmed
BLT-A nonrecipients from recipients who report first receipt in 2005/2006 and
other/unknown years. The second reconstructs CES-D frequency including KP01=3
skips and reverses hopeful/happy items E and H. It does not compute a sum score
or latent factor.

**Only after inspecting aggregate outputs**, optionally export private
household/person-level candidate datasets:

\`\`\`bash
python 02_scripts/20_rapsem_blt2005/03a_build_blt_treatment.py --write-private
python 02_scripts/20_rapsem_blt2005/03b_build_cesd_indicators.py --write-private
\`\`\`

The scripts refuse to overwrite local candidate CSVs in \`01_data/\`.
Do **not** commit these files. Read
[measurement_rules_ifls4.md](measurement_rules_ifls4.md) for the distinction
between questionnaire facts and researcher-chosen scoring.

**Important compatibility warning:** These candidate files are *not* yet inputs
to \`04_build_panel.py\`. Its earlier implementation reads \`KP02\` alone and
does **not** reconstruct skip-dependent item scores; running that panel builder
with a raw-KP02 mapping would produce incorrect mediator availability. It must
be updated and validated once the candidate measures and linkage design are
approved. Do not proceed to \`04_build_panel.py\` yet.

**Stop here until the questionnaire/codebook agrees with our planned variable mapping.** We especially need to verify:

- **2005/06 BLT I, not 2008 BLT or 2013 BLSM.** `b1_ksr1` alone is not guaranteed to be the right final treatment coding source. Inspect other KSR files and data labels.
- **Explicit nonrecipient code.** A missing row or unknown response is NOT automatically untreated.
- **IFLS4 current-household membership codes (`AR01A`).** `PIDLINK` can appear multiple times in the unfiltered roster. We must filter to actual current members before joining.
- **CES-D item type and frequency codes.** We will keep ten *raw items*, and later fit a CFA; do not fabricate sum scores or reverse-code before checking wording.
- **Historical BLT household attribution.** Membership may have changed between payment in 2005 and IFLS4 interview; this is a design threat, not just a merge operation.

## 4. Verify and configure the variables

Inside `02_scripts/20_rapsem_blt2005/` copy:

```bash
cp 02_scripts/20_rapsem_blt2005/study_config.example.json \
   02_scripts/20_rapsem_blt2005/study_config.json
```

Edit `study_config.json` using your actual labels and questionnaire evidence. Fill:

1. Roster: current-member codes and correct `PIDLINK`, `HHID`, `AR01A`, age fields for **each wave**. Set each `approved` flag only after verification.
2. Treatment: the **correct IFLS4 BLT I source**, program selector if necessary, explicitly reported yes/no categories and date meaning. Only set `exposure_assignment_verified=true` after evaluating household splitting and whether the historical recipient household corresponds to the 2007 household.
3. Mediator: the ten `KPTYPE` codes and valid `KP02` categories. The default builder expects *long-form* KP with one row per person-item; verify this against data.
4. Baseline covariates: add approved mappings such as `age` (already from roster), education, employment, sex, baseline housing and assets. Do not automatically treat 2007/2014 values as baseline confounders.
5. Welfare: link the approved `household_welfare_harmonized.csv` generated in Step 5 (or by a trusted independently validated construction).

**Optional covariate configuration example** (replace names only after confirming the codebook):

```json
"baseline_covariates": [
  {
    "approved": true,
    "name": "sex_2000_raw",
    "file": "bk_ar1",
    "level": "person",
    "key": "pidlink",
    "variable": "ar07",
    "aggregation": "none"
  }
]
```

For `level="household"`, `key` must be the household ID field in that source. Repeated household-asset rows require an explicitly justified aggregation such as `sum`, not an automatic arbitrary first record. Special missing codes require review before numeric aggregation; the current script does **not** silently recode them.

## 5. Construct harmonized household welfare (substantive check)

**This step is deliberately not automatic.** Correct poverty measurement is more important than having a fully populated CSV. We need monthly household consumption including verified weekly food, monthly nonfood, yearly nonfood and any additional relevant expenditures, plus own production if appropriate. There must be no double-counting or missing-code-as-zero errors.

Use one of two routes:

**Route A — Preferred if a vetted harmonized PCE file is already available:** Prepare `01_data/04_intermediate/rapsem_blt2005/household_welfare_harmonized.csv` with columns:

```text
wave,hhid,monthly_pce,monthly_poverty_line
ifls3,<actual 2000 household ID>,<verified monthly per-person expenditure>,<matched monthly poverty threshold>
ifls5,<actual 2014/15 household ID>,<verified monthly per-person expenditure>,<matched monthly poverty threshold>
```

Here `monthly_pce` and `monthly_poverty_line` must be in the **same nominal local currency and month/year units for that household's survey period**. Thresholds should match year, geographic area and urban/rural status when applicable. Keep a separate source note documenting whether PCE is nominal or deflated and the exact definition.

**Route B — Build PCE from raw IFLS KS files:**

```bash
cp 02_scripts/20_rapsem_blt2005/welfare_basket.example.json \
   02_scripts/20_rapsem_blt2005/welfare_basket.json
```

Read IFLS3/5 KS questionnaires; fill every `amount_columns`, period multiplier and included item code list in `welfare_basket.json`, including any needed KS0 components. Do **not** approve an incomplete consumption basket. Supply a local matching table:

`01_data/04_intermediate/rapsem_blt2005/poverty_lines_household.csv`

with the columns `wave,hhid,monthly_poverty_line` and real verified BPS thresholds. A header-only template is versioned at `00_documentation/general/poverty_lines_household.template.csv`. Then run:

```bash
python 02_scripts/20_rapsem_blt2005/03_build_welfare.py
```

It calculates **monthly total expenditure / verified current household size** (per-capita), compares it with the poverty line, and creates the harmonized welfare file. It refuses missing KS components, invalid amounts, and incomplete basket approvals. If the questionnaire proves that a missing amount represents **zero expenditure**, list that exact field under `zero_if_missing_columns` in its approved component; otherwise missing amounts stay missing. It does not download or invent poverty lines.

**We cannot compute poverty exit yet until this stage is verified.** Official poverty thresholds and survey expenditure baskets are external inputs, not facts that can be guessed by code.

## 6. Construct the person-level panel

After `study_config.json` approvals and the harmonized welfare file are ready:

```bash
python 02_scripts/20_rapsem_blt2005/04_build_panel.py
python 02_scripts/20_rapsem_blt2005/05_quality_report.py
```

The builder will produce **private, person-level datasets** inside the existing Git-ignored `01_data/` folder:

- `01_data/04_intermediate/rapsem_blt2005/baseline_person_2000.csv`: baseline adult covariates and person/household IDs.
- `01_data/04_intermediate/rapsem_blt2005/blt2005_household_ifls4.csv`: verified historical BLT status linked to IFLS4 households.
- `01_data/04_intermediate/rapsem_blt2005/cesd_items_2007.csv`: ten raw CES-D indicators linked by PIDLINK.
- `01_data/04_intermediate/rapsem_blt2005/person_panel_full.csv`: baseline adults and flags for later waves, BLT, CES-D and welfare.
- `01_data/05_analysis/rapsem_blt2005/baseline_poor_analysis_panel.csv`: people from baseline-poor households, including still-missing follow-up values for transparent attrition audits.

It also generates **aggregate-only** quality reports under `05_outputs/tables/rapsem_blt2005/`.

### Stop/go checks before any estimation

- Unique current-member `PIDLINK` in each survey after filtering by documented membership codes.
- No row multiplication when joining person and household files.
- Historical BLT correctly coded with explicit nonrecipients, and a documented policy on split-off households.
- Ten correctly mapped CES-D items, with correct ordinal response levels and missing codes.
- Complete and comparable PCE at baseline and follow-up, and poverty lines matched to actual interview dates/geography.
- Adequate sample size and transparent attrition from 2000 to 2007 to 2014.
- No post-treatment employment, income, later BLT/BLSM, health or assets silently added to pretreatment covariates.

**Only then** begin propensity overlap/balance diagnostics, AIPW/DiD for total effects, the CES-D CFA and a separate RAPSEM identification/validation exercise. This starter deliberately does not produce ATT or RAPSEM estimates.

## 7. Re-running and safety

The builders refuse to overwrite an existing private analysis dataset. If you intentionally change the mappings and rebuild, first archive the old dataset and keep the accompanying audit reports. Read-only audit reports are regenerated. Source `.dta` files are never changed.

Your existing `.gitignore` ignores `01_data/**`, `00_documentation/**`, and `05_outputs/**`, plus Python virtual environments. Confirm this before `git add` or push. Do **not** commit or share person-level IFLS files. The source and study config are safe to version-control after checking that they contain no private data or credentials.

## Run-order summary

```bash
# In the folder containing IFLS_Project.Rproj (one-time setup):
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r 02_scripts/20_rapsem_blt2005/requirements.txt
python 02_scripts/20_rapsem_blt2005/00_setup.py

# On future terminal sessions, just activate with: source .venv/bin/activate

# After putting IFLS3/4/5 .dta files in separate wave folders:
python 02_scripts/20_rapsem_blt2005/01_inventory.py
python 02_scripts/20_rapsem_blt2005/02_candidate_audit.py
python 02_scripts/20_rapsem_blt2005/02a_review_audit_reports.py
python 02_scripts/20_rapsem_blt2005/02b_focused_code_audit.py
python 02_scripts/20_rapsem_blt2005/02c_measurement_validation.py

# Questionnaire-informed provisional measures and synthetic tests:
python 02_scripts/20_rapsem_blt2005/03a_build_blt_treatment.py
python 02_scripts/20_rapsem_blt2005/03b_build_cesd_indicators.py
python -m pytest 02_scripts/20_rapsem_blt2005/tests/test_candidate_measurement.py -q

# MANUAL GATE: verify variables, codes, poverty thresholds and treatment attribution;
# complete study_config.json; prepare welfare_basket.json if using Route B.

# Only after welfare basket + poverty thresholds are verified (Route B):
python 02_scripts/20_rapsem_blt2005/03_build_welfare.py

# NOT YET: 04_build_panel.py needs KP01/KP02 skip handling and review of
#          household-to-person treatment assignment before any final panel.
# After its revised implementation is approved:
python 02_scripts/20_rapsem_blt2005/04_build_panel.py
python 02_scripts/20_rapsem_blt2005/05_quality_report.py
```

## Data and documentation links

- Official IFLS home and data access: https://www.rand.org/well-being/social-and-behavioral-policy/data/FLS/IFLS.html
- Access terms: https://www.rand.org/well-being/social-and-behavioral-policy/data/FLS/IFLS/access.html
- IFLS4 overview with data/metadata structure: https://catalog.ihsn.org/catalog/2370
- IFLS3 overview: https://catalog.ihsn.org/catalog/2369
- Reference RAPSEM implementation: https://github.com/PsychometricsMZ/RAPSEM