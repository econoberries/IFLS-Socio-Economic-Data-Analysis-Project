# Python-first BLSM 2013 feasibility audit

This is a **Python implementation of the first four R data-audit steps** for our IFLS4–IFLS5 research study. It uses original Stata files, preserves original value labels in the audit outputs, and does not touch raw data.

## Start from your existing IFLS project

Open Terminal in the folder that contains `IFLS_Project.Rproj` (not in this `python/` folder).

```bash
cd "/Users/khaira_abdillah/Documents/IFLS_Causal_Project/IFLS-Socio-Economic-Data-Analysis-Project-main"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r 02_scripts/10_blsm_2013/python/requirements.txt
```

If your project root differs, use the folder with `IFLS_Project.Rproj`. The `.venv/` directory must remain outside Git; check your `.gitignore` or create it outside the repo.

## Run in order

```bash
python 02_scripts/10_blsm_2013/python/01_treatment_audit.py
python 02_scripts/10_blsm_2013/python/02_panel_audit.py
python 02_scripts/10_blsm_2013/python/03_welfare_inventory.py
python 02_scripts/10_blsm_2013/python/04_interview_calendar_audit.py
```

All source files are searched recursively under `01_data/01_raw_dta/ifls4` and `ifls5`. The reports are written locally to `05_outputs/tables/blsm_2013_python/`. The scripts output **aggregate counts or metadata, not individual household records**.

## What each script establishes

| Step | Script | Results |
|---|---|---|
| 1 | `01_treatment_audit.py` | Program labels, recorded receipt, reported first/last years, ambiguous dates; no treatment D yet |
| 2 | `02_panel_audit.py` | Unique persons by wave, unfiltered PIDLINK overlap, tracking-file availability and household split-off summaries |
| 3 | `03_welfare_inventory.py` | Available KS and related modules, row/variable inventory, variable labels; no expenditure aggregation yet |
| 4 | `04_interview_calendar_audit.py` | Candidate interview date fields to verify against documentation and payment timing |

## Identification and implementation roadmap

**Empirical target:** ATT of BLSM receipt in 2013 on change in **real monthly consumption per capita** between IFLS4 (2007–08) and IFLS5 (2014–15), then subgroup ATT by baseline economic status, urban/rural, and baseline household composition.

We cannot fit ATT until we define true nonrecipients, a defensible linked sample, the consumption basket, nominal-to-real adjustment, and baseline covariates. With two waves, parallel trends cannot be checked using multiple pre-treatment time points.

Once those gates pass, the **Python** plan is:

1. Construct and validate the linked panel with `pandas`.
2. Build harmonized consumption with explicit KS item mappings, period conversions and price adjustments.
3. Inspect pretreatment balance, propensity overlap, attrition, clustering, and possible late-2014 transfer contamination.
4. Estimate conventional and doubly robust *panel* DiD ATT using `doubleml` (current `DoubleMLDID`) and/or `differences`.
5. Estimate prespecified baseline **subgroup ATT**; explore CATE only with appropriate assumptions and sample sizes.
6. Consider LATE only after establishing an instrument and its exclusion/relevance/monotonicity conditions.
7. Investigate RAPSEM mediation only with a temporally ordered post-treatment mediator and a valid observational identification argument.

**RAPSEM caveat:** the official implementation is R-based. Python can call the reference R package via `subprocess` / `Rscript` to reproduce results while managing the overall pipeline in Python. A new Python reimplementation of the estimators would need independent validation against the paper and original R code.

## Existing R files

The four R scripts remain available for cross-language checks. They are **not required** for running these Python audits. This repository's existing .dta-to-CSV conversion pipeline also remains unchanged; Python can read the original `.dta` directly.

## Data protection

The IFLS files stay local. Do not upload person-level results, raw survey data, any project virtual environment or automatically generated outputs to GitHub. The audit intentionally stops on ambiguous program labels instead of fabricating BLSM groups.

Research methods protocol: [Causal Inference Methods Lab](https://github.com/econoberries/Causal-Inference-Methods-Lab/blob/main/docs/research/ifls45_blsm2013_att_protocol.md).
