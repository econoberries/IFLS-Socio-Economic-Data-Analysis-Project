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
| `household_size` | Number of approved household members (\(N_{hw}\)) |
| `monthly_pce` | Monthly expenditure per household member |
| `monthly_poverty_line` | Verified poverty threshold, in the same money/time units |
| `log_pce_pl` | Natural log of PCE / poverty line |
| `poor` | 1 = below poverty line, 0 = at/above; missing when relative welfare is invalid |

The longitudinal person panel is a **later step**. Never assume the same
household ID or household composition across IFLS3, IFLS4, and IFLS5.

Notation:

- \(h\) = household in a particular survey wave
- \(w\) = IFLS wave
- \(k\) = consumption component (e.g., weekly food, monthly nonfood)
- \(i\) = selected item/row within a component
- \(N_{hw}\) = eligible current household size

## 2. Step A — Convert expenditure to a monthly basis

Different questions can use **different recall periods**. For each
approved expenditure item, multiply the recorded amount by the factor
that converts its stated period to a month:

\[
e^{(month)}_{ihwk} = f_{wk}\,\sum_{c\in C_{wk}} x_{ihwkc}
\]

where:

- \(x_{ihwkc}\) is the observed expenditure amount from an approved field,
- \(C_{wk}\) is the set of amount fields required for that component,
- \(f_{wk}\) is the *approved* multiplier to monthly units.

Illustrative period conversions (not automatically validated basket rules):

| Recall period | Example multiplier | Reason |
|---|---:|---|
| Previous week | \(52/12 \approx 4.3333\) | 52 weeks / 12 months |
| Previous month | \(1\) | Already monthly |
| Previous 12 months | \(1/12 \approx 0.0833\) | Annual amount divided by 12 |

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

\[
E_{hwk} = \sum_{i\in I_{hwk}} e^{(month)}_{ihwk}
\]

Then add the components:

\[
C_{hw} = \sum_{k=1}^{K_w} E_{hwk}
\]

where \(C_{hw}\) is total monthly household expenditure.

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

\[
N_{hw} = \#\{\text{eligible current household members of }h
\text{ in wave }w\}
\]

The roster function rejects duplicate `PIDLINK` records after filtering.
No arbitrary `drop_duplicates()` is used.

Use **wave-specific** household membership rules in `study_config.json`.
The IFLS4 User's Guide, Vol. 2, printed pp. 38–39, notes that certain
tracked members (`AR01a=11` in IFLS4) were absent in the main fieldwork,
and may be unsuitable for the contemporaneous expenditure denominator.
That is a **warning** for denominator design, not a license to apply
IFLS4 codes blindly to IFLS3 and IFLS5.

## 5. Step D — Monthly per capita expenditure (PCE)

\[
\boxed{\mathrm{PCE}_{hw}=\frac{C_{hw}}{N_{hw}}}
\]

PCE describes average monthly household expenditure **per eligible member**.
It is not the same as wages, income, wealth, or cash-transfer receipt.

If monthly household expenditure is missing, PCE is also missing.
A household without a valid denominator should never receive PCE.

## 6. Step E — Compare PCE with a verified poverty line

Let \(PL_{hw}\) be the correct **monthly poverty threshold per person**,
matched to the household's relevant survey date and geography.

The relative welfare measure is:

\[
R_{hw} = \frac{\mathrm{PCE}_{hw}}{PL_{hw}}
\]

Its natural log is:

\[
\boxed{W_{hw}=\log\left(\frac{\mathrm{PCE}_{hw}}{PL_{hw}}\right)}
\]

For valid positive PCE and poverty-line values:

\[
\mathrm{Poor}_{hw} =
\begin{cases}
1 & \mathrm{PCE}_{hw}<PL_{hw} \quad (W_{hw}<0),\\
0 & \mathrm{PCE}_{hw}\geq PL_{hw} \quad (W_{hw}\geq0).
\end{cases}
\]

Interpretation:

- \(W<0\): PCE is below the poverty line.
- \(W=0\): PCE equals the poverty line.
- \(W>0\): PCE exceeds the poverty line.

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

If \(N=4\), then monthly PCE is Rp 400,000. If a **hypothetical** monthly
poverty line is Rp 500,000 per person, then:

\[
R=400{,}000/500{,}000=0.8,\qquad
W=\log(0.8)\approx -0.2231,\qquad
\mathrm{Poor}=1.
\]

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
**Do not run `04_build_panel.py` yet**: its treatment/missing-data and
CES-D integration still require revision and approval.

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
