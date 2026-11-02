# BLSM 2013 — IFLS4/IFLS5 audit

**Research question:** What is the effect of BLSM receipt in 2013 on change in household economic welfare between IFLS4 (2007–08) and IFLS5 (2014–15)?

**Main estimand:** ATT among actual BLSM recipients; then ATT within pre-specified baseline subgroups (not generic population CATE). Candidate outcome: real monthly household consumption per capita. This is **not yet a validated causal design**.

## How to run

Open `IFLS_Project.Rproj` in RStudio. Run scripts individually from the Console, in order:

```r
source("02_scripts/10_blsm_2013/01_treatment_audit.R")
source("02_scripts/10_blsm_2013/02_panel_audit.R")
source("02_scripts/10_blsm_2013/03_welfare_inventory.R")
source("02_scripts/10_blsm_2013/04_interview_calendar_audit.R")
```

Then open `03_notebooks/02_blsm_2013_ifls4_ifls5_audit.Rmd` and knit to read the recorded checklists and aggregate tables.

All source files are located under `01_data/01_raw_dta/ifls4` and `ifls5`, including nested `household/` folders. **No original data are modified or uploaded**. Non-identifying output counts and variable dictionaries are saved locally to:

```text
05_outputs/tables/blsm_2013/
  00_ksr1_variable_labels.csv
  01_program_codes.csv
  01_receipt_codes.csv
  02_blsm_timing_classification.csv
  03_blsm_first_last_year.csv
  04_ptrack_linkage_counts.csv
  05_splitoff_audit.csv
  06_htrack_linkage_counts.csv
  07_htrack_<variable>.csv
  08_ptrack_<variable>.csv
  09_welfare_file_inventory.csv
  10_welfare_variable_dictionary.csv
  11_interview_date_variable_candidates.csv
```

If a file is missing or variables have changed across IFLS releases, inspect the questionnaire and do not silently recode it.

## Critical checks and decision gates

1. **BLSM program identification:** IFLS5 questionnaire Book 1, KSR3TYPE column C denotes BLSM; KSR17 codes 1=yes and 3=no, with KSR18/KSR22 capturing first/last dates. Verify the actual Stata value labels and code storage. A missing program row is *not* automatically no receipt.
2. **Treatment timing:** Separate 2013 recipients from later receipt/unknown timing, and check interviews relative to the November 2014 program phase. Use 2013 first receipt as a candidate classification, but resolve ambiguous cases before estimating.
3. **Household tracking:** HTRACK14 and PTRACK14 are not interchangeable. PIDLINK links persons; households may split or combine. Determine the unit and sample-definition rule before making a balanced panel.
4. **Outcome:** Build a documented harmonized consumption aggregate from KS modules in both waves. Weekly food, monthly nonfood, annual nonfood, education, housing and own-production require consistent reference periods; deflate nominal Rp values to a constant price base. Avoid mechanically counting cash transfers as consumption.
5. **Subgroups:** Baseline poverty/vulnerability, urban/rural and household composition must be defined using *pre-2013* values only.
6. **Identification:** Candidate method is doubly robust **panel DiD ATT**. Conditional parallel trends, overlap, stable comparison, interference, program co-exposures and attrition must be justified. With only IFLS4 and IFLS5, a pre-treatment parallel-trends test is unavailable for many outcomes.
7. **Inference:** Check household clustering and the IFLS survey design. No LATE is identified without an additional justified IV or assignment rule.
8. **RAPSEM:** Later feasibility exercise, **not ATT estimation**. Identify a post-BLSM, pre-outcome latent mediator and defend the structural interaction exclusion restriction; simultaneous IFLS5 mediator/outcome does not itself establish timing.

## Why BLSM 2013

SMERU describes the 2013 BLSM distribution as two phases in June/July and September/October, with total compensation Rp600,000 per target household. The later 2014 cash-transfer round creates possible exposure contamination during IFLS5 interviews. Eligibility was targeted, not randomized.

## Sources

- RAND IFLS5 Household Questionnaire, Book 1 KSR: https://www.rand.org/content/dam/rand/pubs/working_papers/WR1100/WR1143z3/RAND_WR1143z3.pdf
- IFLS5 User's Guide: https://studylib.net/doc/12699099/user-s-guide-for-the-indonesia-family-life-survey--wave-5...
- SMERU 2013 BLSM: https://www.smeru.or.id/en/publication/use-social-protection-card-kps-and-implementation-2013-unconditional-cash-transfer
