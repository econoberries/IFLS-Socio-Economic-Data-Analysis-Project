# IFLS4 measurement decisions — BLT 2005/06 and psychological distress

**Status:** questionnaire coding verified; derived variables are **provisional**.
No observational identification or RAPSEM causal assumptions are approved by
this document.

All source information below is from the **IFLS4/2007 questionnaires uploaded
for review** and RAND's *User's Guide for the Indonesia Family Life Survey,
Wave 4, Volume 2*. No IFLS microdata are committed to this repository.

## 1. Household cash transfers — Book 1, p. 9, Section KSR

File audited: IFLS4 `b1_ksr1.dta`; one record per `HHID07 × KSR3TYPE`.

| Question/field | Verified questionnaire definition |
|---|---|
| `KSR3TYPE=A` | `Program Kompensasi Pengurangan Subsidi BBM – Bantuan Langsung Tunai`, unconditional cash transfer |
| `KSR3TYPE=B` | `Program Bantuan Tunai Bersyarat – Keluarga Harapan`, conditional cash transfer |
| `KSR17` | Whether the household **ever** received a transfer from that program; A uses 1 yes, 3 no |
| `KSR17=6` | "No program" option explicitly displayed in program B; **not** a valid BLT-A nonrecipient code |
| `KSR18` | Month/year of **first** transfer |
| `KSR22` | Month/year of **last** transfer |

The candidate rule used by `03a_build_blt_treatment.py` is:

- `1`: BLT-A `KSR17=1` **and first transfer year is 2005 or 2006**.
- `0`: BLT-A `KSR17=3` (self-reported never received BLT).
- `NA`: reported BLT receipt but the first year is outside 2005/06,
  unknown, or special; also all unrecognized receipt codes.

This is a **research coding choice**, not literally a questionnaire-defined
treatment indicator. A "yes" with a later first transfer is **not** silently
reassigned to the control group. The interview year is 2007–08. A 2007
household can differ from the 2005 household that actually received BLT;
validate splits/merges, selective attrition, and baseline membership before
claiming person-level exposure. Questionnaire code 9 remains unclassified.

## 2. Psychological distress — Book 3B, p. 12, Section KP

File audited: IFLS4 `b3b_kp.dta`; one row per `PIDLINK × KPTYPE`.

| Field | Verified questionnaire definition |
|---|---|
| `KPTYPE` | A–J: ten feelings during the prior week |
| `KP01=1` | Yes, felt the specified feeling; ask `KP02` |
| `KP01=3` | No, did not feel it; **skip KP02** |
| `KP02=1` | Rarely (≤ 1 day) |
| `KP02=2` | Some days (1–2 days) |
| `KP02=3` | Occasionally (3–4 days) |
| `KP02=4` | Most of the time (5–7 days) |

Items E (hopeful about the future) and H (happy) are positively worded.

Proposed candidate scoring in `03b_build_cesd_indicators.py`:

1. `KP01=3` with a genuinely blank `KP02`: raw frequency 0.
2. `KP01=1` and `KP02` in 1–4: raw frequency `KP02-1` (0–3).
3. Otherwise: missing/unresolved, without imputing a symptom absence.
4. Reverse positive E and H as `3 - raw frequency`; other items retain
   raw frequency. Higher values **tentatively** represent greater distress.

This reconstruction is an **analytic convention** following the questionnaire
routing, not an original survey variable or a validated latent-factor model.
It requires subsequent distribution checks and psychometric evaluation.
Do not use a plain `KP02` count as a CES-D score: its many missing values are
structural skips after `KP01=3`. Retain ten indicators; no total score, latent
score, or causal mediation parameter is generated at this stage.

## 3. Missing and special response codes

RAND IFLS4 *User's Guide*, Volume 2, printed pp. 15–16:
numeric special-code final digits 5 out-of-range, 6 not applicable,
7 refused, 8 don't know, and 9 missing; for dates, 9998/9999 are not
calendar years. Confirm meaning of each variable's stored codes and
associated X indicator before using them analytically.

## 4. Roster and longitudinal linkage

RAND IFLS4 *User's Guide*, Volume 2, printed pp. 21–25, 38–39:
`PIDLINK` is used for person-level longitudinal tracking. The cumulative
Book K roster can list a person in more than one 2007 household. For 2007,
`AR01a` values 1, 2, 5, 11 indicate found members; 0, 3 are
deceased/moved; 6 indicates duplicate entries that should be ignored.
Code 11 denotes found during tracking (absent during the main field survey)
and may need to be excluded from expenditure household-size denominators.

Research questions still open:
- How to attribute 2005 BLT benefits to the 2007 and 2014 respondents after
  split-offs and changing household composition?
- Whether the analysis unit should be **persons** exposed to household BLT
  (with a person-level outcome), or households with a defined aggregate
  psychological mediator (which is not directly measured).
- How to select pretreatment IFLS3 covariates and handle attrition, welfare,
  and contamination by later transfers.
- Whether RAPSEM identification assumptions can be justified for a
  nonrandomized transfer program.

## 5. Software safety and scope

- `03a_build_blt_treatment.py` and `03b_build_cesd_indicators.py` produce
  **aggregate-only reports by default**. `--write-private` explicitly writes
  person/household-level candidate files under Git-ignored `01_data/`;
  these scripts refuse to overwrite existing files.
- They do **not** supply approved input to `04_build_panel.py`. The current
  panel builder reads raw `KP02` and does not reconstruct skipped responses,
  so it must be revised and checked before use.
- The scripts make **no** decisions about observational ignorability, valid
  instruments, mediator–outcome confounding, treatment positivity, or RAPSEM
  identification. Those are separate design/analysis tasks.
