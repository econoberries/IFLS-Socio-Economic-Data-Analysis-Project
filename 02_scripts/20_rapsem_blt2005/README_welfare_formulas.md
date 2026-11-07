# IFLS3–IFLS5 household welfare: formulas and data construction

This note explains the **definitions, formulas, and coding choices** in
[03_build_welfare.py](03_build_welfare.py). It is written for someone learning
Python and working with IFLS data.

**Research use:** IFLS3 (2000) is the proposed *pretreatment baseline*;
IFLS5 (2014–15) is the proposed household-welfare follow-up for our
BLT 2005–06 → psychological distress → later welfare project.

> **Status: not yet validated with complete IFLS3/IFLS5 baskets.**
> The script implements formulas, not an official IFLS/BPS welfare series.
> It will not run until the consumption basket, membership rules, and local
> poverty-line inputs are reviewed and explicitly approved. No poverty
> thresholds are embedded or invented.

## 1. What is the unit of analysis?

We first construct **one welfare row per household per survey wave**:

| Column | Meaning |
|---|---|
| `wave` | `ifls3` (2000) or `ifls5` (2014–15) |
| `hhid` | Household identifier within that wave |
| `household_size` | Number of approved household members ($N_{hw}$) |
| `monthly_pce` | Monthly expenditure per household member |
| `monthly_poverty_line` | Verified poverty threshold, in the same money/time units |
| `log_pce_pl` | Natural log of PCE / poverty line |
| `poor` | 1 = below poverty line, 0 = at/above; missing when relative welfare is invalid |

The longitudinal person panel is a **later step**. Never assume the same
household ID or household composition across IFLS3, IFLS4, and IFLS5.

Notation:

- $h$ = household in a particular survey wave
- $w$ = IFLS wave
- $k$ = consumption component (e.g., weekly food, monthly nonfood)
- $i$ = selected item/row within a component
- $N_{hw}$ = eligible current household size

## 2. Step A — Convert expenditure to a monthly basis

Different questions can use **different recall periods**. For each
approved expenditure item, multiply the recorded amount by the factor
that converts its stated period to a month:

$$
e^{(month)}_{ihwk} = f_{wk}\,\sum_{c\in C_{wk}} x_{ihwkc}
$$

where:

- $x_{ihwkc}$ is the observed expenditure amount from an approved field,
- $C_{wk}$ is the set of amount fields required for that component,
- $f_{wk}$ is the *approved* multiplier to monthly units.

Illustrative period conversions (not automatically validated basket rules):

| Recall period | Example multiplier | Reason |
|---|---:|---|
| Previous week | $52/12 \approx 4.3333$ | 52 weeks / 12 months |
| Previous month | $1$ | Already monthly |
| Previous 12 months | $1/12 \approx 0.0833$ | Annual amount divided by 12 |

**Important:** The actual fields and recall period must be verified against
the **IFLS3 and IFLS5** questionnaires and codebooks, independently.
The IFLS4 Book 1 questionnaire confirms that some food amounts refer to the
past week and that purchased and self-produced food can be recorded
separately; this is **not proof that all IFLS3/IFLS5 files use identical
questions or amounts**.

In the JSON settings, `amount_columns` identifies the fields to sum.
For instance, when verified and relevant, an item may include **purchases
plus the value of own-produced or received consumption**. Exclude duplicate
aggregates, transfers that are not consumption, and fields with overlapping
coverage. The `b1_ks0` aggregates and any missing consumption sections must
be audited before marking a basket complete.

### How the code handles a missing item

By default, when **any required amount field** of a selected row is missing,
the item's monthly amount is missing; it is **not automatically zero**.
Relevant survey special codes must be entered in `missing_codes`.

Only set `zero_if_missing_columns` for fields where the questionnaire and
data documentation support an explicit missing-as-zero interpretation.
Blank/NA, refused, don't know, and not-applicable are not all the same thing.

## 3. Step B — Calculate total monthly household expenditure

First add all **recorded approved items** within each component:

$$
E_{hwk} = \sum_{i\in I_{hwk}} e^{(month)}_{ihwk}
$$

Then add the components:

$$
C_{hw} = \sum_{k=1}^{K_w} E_{hwk}
$$

where $C_{hw}$ is total monthly household expenditure.

The script uses a **strict completeness rule for the configured fields**:

- Each configured component must produce a household amount.
- No selected item in that component may have a missing required amount.
- Otherwise `monthly_total_expenditure` and PCE remain missing for that household.

**Limitation:** This checks completeness of *configured components and
observed selected rows*. It does **not** by itself prove that every
questionnaire item, every expected item-code row, or an omitted KS0
component was included. Researchers must validate complete item coverage
before setting the basket approval flags.

## 4. Step C — Count eligible current household members

From the wave's Book K roster, retain only **verified member-status codes**,
then count unique linked people per household:

$$
N_{hw} = \#\{\text{eligible current household members of }h
\text{ in wave }w\}
$$

The roster function rejects duplicate `PIDLINK` records after filtering.
No arbitrary `drop_duplicates()` is used.

Use **wave-specific** household membership rules in `study_config.json`.
The IFLS4 User's Guide, Vol. 2, printed pp. 38–39, notes that certain
tracked members (`AR01a=11` in IFLS4) were absent in the main fieldwork,
and may be unsuitable for the contemporaneous expenditure denominator.
That is a **warning** for denominator design, not a license to apply
IFLS4 codes blindly to IFLS3 and IFLS5.

## 5. Step D — Monthly per capita expenditure (PCE)

$$
\boxed{\mathrm{PCE}_{hw}=\frac{C_{hw}}{N_{hw}}}
$$

PCE describes average monthly household expenditure **per eligible member**.
It is not the same as wages, income, wealth, or cash-transfer receipt.

If monthly household expenditure is missing, PCE is also missing.
A household without a valid denominator should never receive PCE.

## 6. Step E — Compare PCE with a verified poverty line

Let $PL_{hw}$ be the correct **monthly poverty threshold per person**,
matched to the household's relevant survey date and geography.

The relative welfare measure is:

$$
R_{hw} = \frac{\mathrm{PCE}_{hw}}{PL_{hw}}
$$

Its natural log is:

$$
\boxed{W_{hw}=\log\left(\frac{\mathrm{PCE}_{hw}}{PL_{hw}}\right)}
$$

For valid positive PCE and poverty-line values:

$$
\mathrm{Poor}_{hw} =
\begin{cases}
1 & \mathrm{PCE}_{hw}<PL_{hw} \quad (W_{hw}<0),\\
0 & \mathrm{PCE}_{hw}\geq PL_{hw} \quad (W_{hw}\geq0).
\end{cases}
$$

Interpretation:

- $W<0$: PCE is below the poverty line.
- $W=0$: PCE equals the poverty line.
- $W>0$: PCE exceeds the poverty line.

**Zero PCE needs special attention.** Its log is not finite. For now, the
script deliberately sets both `log_pce_pl` and `poor` to missing for a
zero-PCE household so that the analyst reviews its data. A valid, verified
zero PCE would ordinarily be below any positive poverty line; that is a
separate decision to implement after checking the raw data.

`monthly_poverty_line` is **not calculated by this script**. Supply a
verified, household-matched file with:

```csv
wave,hhid,monthly_poverty_line
```

This file belongs under the local, Git-ignored `01_data/` folder.
Match the **actual interview year, geography, urban/rural status when
appropriate, currency, and period**. Poverty thresholds from two different
years are **not** interchangeable nominal amounts.

### Worked example — hypothetical only

Suppose a household reports:

| Component | Raw amount | Monthly equivalent |
|---|---:|---:|
| Food (past week) | Rp 300,000 | Rp 1,300,000 (= 300,000 × 52/12) |
| Nonfood (past month) | Rp 200,000 | Rp 200,000 |
| Nonfood (past year) | Rp 1,200,000 | Rp 100,000 (= 1,200,000 / 12) |
| **Total** | | **Rp 1,600,000** |

If $N=4$, then monthly PCE is Rp 400,000. If a **hypothetical** monthly
poverty line is Rp 500,000 per person, then:

$$
R=400{,}000/500{,}000=0.8,\qquad
W=\log(0.8)\approx -0.2231,\qquad
\mathrm{Poor}=1.
$$

These numbers are **an illustration, not IFLS measurements or an official
Indonesian poverty line**.

## 7. What files and settings are needed?

The script reads:

1. Local source `.dta` files for IFLS3 and IFLS5 (recursively under
   `01_data/01_raw_dta/`).
2. `study_config.json`: approved roster fields and current-member codes.
3. `welfare_basket.json`: approved item groups, amount columns, item
   selectors, period multipliers, special codes, and complete-basket flags.
4. A verified household poverty-line CSV as specified in
   `welfare_basket.json`.

Template configuration: [welfare_basket.example.json](welfare_basket.example.json).
Both templates start **unapproved on purpose**. Keep completed local mappings
and underlying data out of GitHub, as indicated in `.gitignore`.

To set up the basket file from the repository root:

```bash
cp 02_scripts/20_rapsem_blt2005/welfare_basket.example.json \
   02_scripts/20_rapsem_blt2005/welfare_basket.json
```

Run **only after confirming all components**:

```bash
python 02_scripts/20_rapsem_blt2005/03_build_welfare.py
```

The script will stop when needed approvals, source files, or poverty lines
are absent. It will **not** generate plausible-looking values to fill gaps.

## 8. Outputs

Aggregate reports, safe for repeated inspection:

- `05_outputs/tables/rapsem_blt2005/03_welfare_component_audit.csv`
- `05_outputs/tables/rapsem_blt2005/03_welfare_summary.csv`

Private household-level file (created only when everything passes checks):

- `01_data/04_intermediate/rapsem_blt2005/household_welfare_harmonized.csv`

The private CSV includes `wave`, `hhid`, `monthly_pce`,
`monthly_poverty_line`, `log_pce_pl`, `poor`, `household_size`.
The builder refuses to overwrite an existing private CSV.

The downstream panel builder currently expects these specific column names.
**Script 04 has now been updated** to merge the candidate 03a BLT and 03b
KP01/KP02-adjusted CES-D outputs. Do not run it with real data until historical
BLT household exposure, IFLS3/IFLS5 welfare, roster rules, and all approval
settings have actually been validated.

## 9. Checklist before accepting the welfare measure

- [ ] Cross-check IFLS3 and IFLS5 KS questionnaires and codebooks separately.
- [ ] Verify every `amount_columns` field, allowed `include_codes`, and
      treatment of own-produced/received consumption.
- [ ] Map any KS0 and other components without double counting.
- [ ] Check item coverage and structural skips, not just component totals.
- [ ] Approve survey-specific roster membership and denominator rules.
- [ ] Validate 0, negative, special-code, and missing expenditure cases.
- [ ] Verify poverty lines by interview year, geographic area, and units.
- [ ] Examine household-level summary distributions and sample attrition.
- [ ] Decide how real vs. nominal welfare and changing households should
      be handled in causal inference.

**Key distinction:** Writing Python code for welfare aggregation is
straightforward; verifying the **economic meaning and comparability**
of those aggregates is the substantive research task.

---

## 10. Quality checks after constructing the person panel (Script 05)

Once **Script 04** has successfully created
`01_data/04_intermediate/rapsem_blt2005/person_panel_full.csv`, run:

```bash
python 02_scripts/20_rapsem_blt2005/05_quality_report.py
```

The simplified [05_quality_report.py](05_quality_report.py) **does not
construct welfare, BLT treatment, CES-D scores, or causal estimates**.
It only reads the private person-level panel and saves two **aggregate**
quality-control tables. It does not publish any individual or household ID.

### 10.1 Variable completeness and missing percentages

For each variable $X_j$ in the person panel, define:

- $N$: total person rows in the **full baseline-adult panel**.
- $N_{\mathrm{observed},j}$: number of rows with a nonmissing $X_j$.
- $N_{\mathrm{missing},j}$: number of rows with missing $X_j$.

The basic identity is:

$
N = N_{\mathrm{observed},j} + N_{\mathrm{missing},j}.
$

The percentage of missing values is:

$
\boxed{
\mathrm{MissingPct}(X_j)
=
\frac{N_{\mathrm{missing},j}}{N}\times100
}
$

The percentage of observed values would be $100-\mathrm{MissingPct}(X_j)$.
The script also reports **`unique_values`**, the count of *distinct
nonmissing* observed values of that variable, not the number of people.
For a binary response with both 0 and 1 present, this is 2; for `PIDLINK`
it will usually equal the number of unique people. No actual PIDLINK values
appear in the aggregate output.

The first report is:

`05_outputs/tables/rapsem_blt2005/05_variable_completeness.csv`

| Column | How to read it |
|---|---|
| `variable` | Name of a column in the panel |
| `n_total` | Number of baseline-adult person rows |
| `n_observed` | Count of nonmissing values for this variable |
| `n_missing` | Count of missing values for this variable |
| `missing_pct` | $100\times n_{\mathrm{missing}}/n_{\mathrm{total}}$, rounded to 2 decimal places |
| `unique_values` | Number of distinct nonmissing values |

**Example (invented data):** Suppose a panel has 10 individuals, of whom 7
have an observed `blt_2005` code and 3 have missing treatment status.
Then `n_total=10`, `n_observed=7`, `n_missing=3`,
`missing_pct=30.00`. If the 7 observed values contain both 0 and 1,
`unique_values=2`.

Notice that **0 (a recorded no) is not a missing value**. Likewise, the
CES-D skip logic was handled by Script 03b; zero-valued scored items are
observed values, not missing responses. Unclassified BLT status remains
missing rather than being treated as the control group.

The output is sorted by `missing_pct`, from highest to lowest, making
variables with the greatest amount of missing data easy to find.

### 10.2 Treatment, poverty, mediator, and sample-selection distributions

The second report is:

`05_outputs/tables/rapsem_blt2005/05_selection_and_treatment_counts.csv`

It has three columns: `variable`, `value`, and `n`.
For each selected variable, it counts how many **person rows** have each
observed category, and includes a separate `<MISSING>` category.

| Variable | Why we check it |
|---|---|
| `blt_2005` | How many baseline adults have candidate BLT=1, 0, or missing |
| `baseline_poor` | Number flagged as poor in IFLS3 by Script 04 |
| `eligible_all_core` | Number flagged with the core observed variables by Script 04 |
| `poor_ifls3` / `poor_ifls5` | Baseline and follow-up poverty categories, including missing |
| `poverty_exit_2014` | Among the baseline-poor, whether observed later welfare is above poverty threshold |
| `observed_ifls4` / `observed_ifls5` | Presence in each wave's filtered roster |
| `observed_cesd` | Whether at least one candidate CES-D indicator is available |
| `cesd_observed_items` | Count of valid CES-D indicators (0–10 when available) |
| `cesd_complete_10` | Whether all ten candidate indicators are observed |

A missing selected column is reported in Terminal and skipped, not invented.

**Interpretation warnings specific to our study:**

1. **The denominator is individuals, not households.** Multiple people
   in one IFLS4 household share the same candidate BLT value; multiple
   people in one IFLS5 household may share the same welfare outcome.
   These counts are not independent household observations.
2. **Not all missingness is panel attrition.** A missing `poor_ifls5`
   may arise from failure to follow a person, absent household expenditure,
   absent poverty thresholds, or invalid PCE values. Use
   `observed_ifls5` alongside the welfare variables to distinguish
   these cases.
3. **`baseline_poor=False` need not mean known nonpoor.** In Script 04
   this boolean is False also when baseline poverty status is missing.
   Inspect `poor_ifls3` directly when describing baseline poverty.
4. **`eligible_all_core=True` means at least one valid CES-D item**,
   not necessarily all ten and not a validated CFA/RAPSEM sample.
   Inspect `cesd_complete_10` separately.
5. **A classified BLT value is still provisional.** The historical
   2005–06 assignment to members of a 2007 household requires a separate
   study-design assessment.

### 10.3 Example of missingness versus sample loss

Imagine (hypothetically) 1,000 IFLS3 baseline adults:

| Check | Individuals |
|---|---:|
| Baseline adults | 1,000 |
| Present in the IFLS4 filtered roster | 850 |
| Present in the IFLS5 filtered roster | 760 |
| Valid IFLS5 log welfare | 700 |
| Candidate BLT code observed | 810 |

The IFLS5 roster linkage rate is $760/1000=76\%$, but valid
follow-up welfare is only $700/1000=70\%$. The difference can reflect
incomplete expenditure or poverty-line information **even for people
who were found in IFLS5**. These marginal counts cannot establish how
many people have *all* required variables simultaneously; use the
joint `eligible_all_core` flag to inspect that overlap.

All example figures are invented for illustration, not results from IFLS.

### 10.4 How to use the quality reports in our causal project

Script 05 should be used to spot problematic missingness, diagnose
retention between waves, and guide later checks of **differential
attrition between BLT and non-BLT groups**. It does not directly
estimate attrition effects, assess overlap or balance, or prove
sequential ignorability, rank preservation, or any RAPSEM
identification assumption.

This stage is complete **only after the actual IFLS panel exists and the
summary reports have been inspected**.

You can test the report calculations with synthetic records at any time:

```bash
python -m pytest -q 02_scripts/20_rapsem_blt2005/tests/test_quality_report.py
```

The two `05_*.csv` audit files live under Git-ignored `05_outputs/`.
The input `person_panel_full.csv` stays under Git-ignored `01_data/`.
