"""Aggregate quality-control report for the constructed panel; no records exported."""
import pandas as pd
from common import intermediate_dir,save_report

p=intermediate_dir()/'person_panel_full.csv'
if not p.exists():raise SystemExit('Run 04_build_panel.py after finishing approved variable mappings.')
d=pd.read_csv(p,dtype='string')
rows=[]
for col in d:
    rows.append({'variable':col,'n_total':len(d),'n_observed':int(d[col].notna().sum()),
                 'missing_pct':round(float(d[col].isna().mean()*100),2),
                 'unique_values':int(d[col].nunique(dropna=True))})
save_report(pd.DataFrame(rows),'05_variable_completeness.csv')
reports=[]
for col in ['blt_2005','baseline_poor','eligible_all_core','poor_ifls3','poor_ifls5','cesd_observed_items']:
    if col in d:
        vc=d[col].fillna('<MISSING>').value_counts().rename_axis('value').reset_index(name='n')
        vc.insert(0,'variable',col)
        reports.append(vc)
if reports:save_report(pd.concat(reports,ignore_index=True),'05_selection_and_treatment_counts.csv')
print('This report is descriptive, not evidence of causal identification. Confirm cross-wave IDs, sample loss and plausibility.')
