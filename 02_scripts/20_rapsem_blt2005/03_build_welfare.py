"""Build harmonized PCE only after item mapping, reference periods and basket completeness are approved.

No default consumption values or poverty lines are generated. This program stops
rather than treat partially mapped baskets as complete household welfare.
"""
import json
import numpy as np
import pandas as pd
from common import (script_dir,project_root,approved,read_config,stata,
                    normalized,require_columns,assert_unique,intermediate_dir,save_report)

p=script_dir()/'welfare_basket.json'
if not p.exists():raise SystemExit('Copy welfare_basket.example.json to welfare_basket.json, audit KS codebooks and complete all component mappings.')
cfg=json.loads(p.read_text(encoding='utf-8'))
approved(cfg)
rosters=read_config()['rosters']
all_out=[]; audit=[]
for wave in ('ifls3','ifls5'):
    if not cfg.get(f'basket_complete_{wave}',False):
        raise ValueError(f'{wave} basket_complete flag is false. Verify ALL consumption components, including relevant KS0, before building PCE.')
    r=rosters[wave];approved(r)
    if not r['current_codes']:raise ValueError('Current household member codes required')
    roster,_=stata(wave,r['file'])
    require_columns(roster,[r['pid'],r['household'],r['membership']],f'{wave} roster')
    mask=normalized(roster[r['membership']]).isin([str(x) for x in r['current_codes']])
    roster=roster.loc[mask,[r['pid'],r['household']]].copy()
    roster['person_id']=normalized(roster[r['pid']]);roster['hhid']=normalized(roster[r['household']])
    roster=roster.dropna(subset=['person_id','hhid'])
    assert_unique(roster,'person_id',f'{wave} current roster')
    sizes=roster.groupby('hhid').size().rename('household_size').reset_index()
    pieces=[]
    for j,sp in enumerate(cfg['components'][wave]):
        if not sp['amount_columns'] or (not sp.get('all_rows_approved') and not sp.get('include_codes')):
            raise ValueError(f'{wave} {sp["file"]}: amount_columns or approved item filters missing.')
        factor=float(sp['multiply_to_monthly'])
        if factor<=0 or not np.isfinite(factor):raise ValueError('Invalid period conversion factor')
        d,_=stata(wave,sp['file'])
        needed=[sp['household']]+list(sp['amount_columns'])
        if sp.get('item_column'):needed.append(sp['item_column'])
        require_columns(d,needed,f'{wave} {sp["file"]}')
        d=d.copy()
        d['hhid']=normalized(d[sp['household']])
        d=d.loc[d['hhid'].notna()]
        if not sp.get('all_rows_approved'):
            d=d.loc[normalized(d[sp['item_column']]).isin([str(k) for k in sp['include_codes']])]
        if d.empty:raise ValueError(f'{wave} {sp["file"]}: no rows after approved filters; check codes.')
        vals=[]
        for a in sp['amount_columns']:
            s=normalized(d[a]);s=s.mask(s.isin([str(v) for v in cfg.get('missing_codes',[])]))
            v=pd.to_numeric(s,errors='coerce')
            if a in sp.get('zero_if_missing_columns',[]):
                v=v.fillna(0)
            vals.append(v)
        stack=pd.concat(vals,axis=1)
        stack.columns=sp['amount_columns']
        item=stack.sum(axis=1,min_count=len(vals))*factor
        if (item.dropna()<0).any():raise ValueError(f'{wave} {sp["file"]}: negative expenditure found; review values and special codes.')
        d['amount']=item
        agg=d.groupby('hhid',dropna=False).agg(total=('amount',lambda s:s.sum(min_count=1)),n_rows=('amount','size'),n_missing=('amount',lambda s:int(s.isna().sum()))).reset_index()
        label=f'part{j+1}_{sp["file"]}'
        agg=agg.rename(columns={'total':label,'n_rows':label+'_rows','n_missing':label+'_missing'})
        pieces.append(agg)
        audit.append(dict(wave=wave,file=sp['file'],selected_rows=len(d),total_missing_item_values=int(d['amount'].isna().sum()),households=agg.shape[0]))
    w=sizes
    for a in pieces:w=w.merge(a,on='hhid',how='left',validate='one_to_one')
    total_cols=[c for c in w.columns if c.startswith('part') and '_rows' not in c and '_missing' not in c]
    has_full=w[total_cols].notna().all(axis=1)
    has_no_missing=w[[c for c in w if c.endswith('_missing')]].fillna(1).eq(0).all(axis=1)
    w['monthly_total_expenditure']=w[total_cols].sum(axis=1,min_count=len(total_cols)).where(has_full & has_no_missing)
    w['monthly_pce']=w['monthly_total_expenditure']/w['household_size']
    w['wave']=wave
    all_out.append(w)
all_welfare=pd.concat(all_out,ignore_index=True)
poverty_path=project_root()/cfg['poverty_lines_file']
if not poverty_path.exists():
    raise FileNotFoundError(f'Missing verified poverty lines {poverty_path}. Required: wave, hhid, monthly_poverty_line.')
pl=pd.read_csv(poverty_path,dtype='string')
require_columns(pl,['wave','hhid','monthly_poverty_line'],'poverty line source')
pl['hhid']=normalized(pl['hhid'])
assert_unique(pl[['wave','hhid']].assign(wave_hh=pl['wave']+'|'+pl['hhid']),'wave_hh','poverty lines')
pl['monthly_poverty_line']=pd.to_numeric(pl['monthly_poverty_line'],errors='coerce')
if not pl['monthly_poverty_line'].dropna().gt(0).all():raise ValueError('Poverty lines must be positive.')
merged=all_welfare.merge(pl[['wave','hhid','monthly_poverty_line']],on=['wave','hhid'],how='left',validate='one_to_one')
merged['log_pce_pl']=np.log(merged['monthly_pce']/merged['monthly_poverty_line'])
merged['poor']=(merged['log_pce_pl']<0).astype('Int64').where(merged['log_pce_pl'].notna())
summary=merged.groupby('wave').agg(households=('hhid','size'),with_valid_welfare=('log_pce_pl','count'),median_pce=('monthly_pce','median')).reset_index()
save_report(pd.DataFrame(audit),'03_welfare_component_audit.csv')
save_report(summary,'03_welfare_summary.csv')
out=intermediate_dir()/'household_welfare_harmonized.csv'
if out.exists():raise FileExistsError(f'{out} already exists. Back up and remove it yourself before rebuilding.')
merged[['wave','hhid','monthly_pce','monthly_poverty_line','log_pce_pl','poor','household_size']].to_csv(out,index=False)
print('CREATED private harmonized welfare:',out)
print('STOP: verify welfare distributions, item aggregation, official poverty thresholds, year and price compatibility.')
