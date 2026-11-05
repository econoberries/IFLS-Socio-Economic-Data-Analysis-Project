"""Validated IFLS3 -> IFLS4 -> IFLS5 person panel construction.

Requires explicit approvals for roster, BLT, mediator and welfare mappings.
Never interprets an absent BLT record as a nonrecipient. Keeps attrition flags.
No propensity, CFA, ATT or RAPSEM estimation is done here.
"""
import numpy as np
import pandas as pd
from common import (read_config,approved,stata,normalized,require_columns,
                    assert_unique,read_local_csv,save_report,save_private,analysis_dir,intermediate_dir)

cfg=read_config()
for wave in ('ifls3','ifls4','ifls5'):approved(cfg['rosters'][wave])
approved(cfg['treatment']);approved(cfg['mediator']);approved(cfg['welfare'])
if not cfg['treatment'].get('exposure_assignment_verified',False):
    raise ValueError('Confirm historical BLT 2005 exposure vs IFLS4 household split-offs before building the study panel.')

def roster(wave):
    r=cfg['rosters'][wave]
    if not r['current_codes']:raise ValueError(f'{wave}: current member codes must be verified.')
    df,_=stata(wave,r['file'])
    need=[r['pid'],r['household'],r['membership'],r['age']]
    require_columns(df,need,f'{wave} roster')
    df=df.loc[normalized(df[r['membership']]).isin([str(x) for x in r['current_codes']]),need].copy()
    out=pd.DataFrame({
        'pidlink':normalized(df[r['pid']]),
        f'hhid_{wave}':normalized(df[r['household']]),
        f'age_{wave}':pd.to_numeric(df[r['age']],errors='coerce')})
    out=out.dropna(subset=['pidlink',f'hhid_{wave}'])
    out.loc[~out[f'age_{wave}'].between(0,115),f'age_{wave}']=np.nan
    assert_unique(out,'pidlink',f'{wave} roster after current-member filter')
    return out

base=roster('ifls3')
base=base.loc[base['age_ifls3'].ge(int(cfg['analysis'].get('minimum_age_ifls3',18)))].copy()
if base.empty:raise ValueError('No baseline adults found. Check age coding/current member codes.')

for var in cfg.get('baseline_covariates',[]):
    if not var.get('approved',False):raise ValueError(f'Baseline covariate {var.get("name")} lacks approval')
    d,_=stata('ifls3',var['file'])
    level=var['level']
    if level not in ('person','household'):raise ValueError('baseline covariate level must be person/household')
    left_key='pidlink' if level=='person' else 'hhid_ifls3'
    require_columns(d,[var['key'],var['variable']],f'baseline {var["name"]}')
    vals=d[[var['key'],var['variable']]].copy()
    vals['_key']=normalized(vals[var['key']]);vals=vals.loc[vals['_key'].notna()].copy()
    method=var.get('aggregation','none')
    if method=='none':
        if vals['_key'].duplicated().any():
            raise ValueError(f'{var["name"]}: multiple rows per {level}. Specify validated aggregation or choose a one-row file.')
        vals=vals[['_key',var['variable']]].copy()
    elif method in ('sum','mean','max','min'):
        num=pd.to_numeric(vals[var['variable']],errors='coerce')
        vals=vals.assign(_value=num).groupby('_key',as_index=False).agg(_value=('_value',method))
        vals=vals.rename(columns={'_value':var['variable']})
    else:raise ValueError(f'Unknown aggregation {method}')
    vals=vals.rename(columns={'_key':left_key,var['variable']:var['name']})
    if var['name'] in base.columns:raise ValueError(f'Duplicate baseline variable name {var["name"]}')
    base=base.merge(vals,on=left_key,how='left',validate='many_to_one')

p4=roster('ifls4');p5=roster('ifls5')
master=base.merge(p4,on='pidlink',how='left',validate='one_to_one',indicator='m4')
master['observed_ifls4']=master.pop('m4').eq('both')
master=master.merge(p5,on='pidlink',how='left',validate='one_to_one',indicator='m5')
master['observed_ifls5']=master.pop('m5').eq('both')

t=cfg['treatment']
tdf,_=stata(t['wave'],t['file'])
if t['wave']!='ifls4':raise ValueError('The treatment source for this design must be the IFLS4 retrospective program record')
needed=[t['household'],t['receipt_column']]
if t.get('program_selector_column'):needed.append(t['program_selector_column'])
if t.get('receipt_year_column'):needed.append(t['receipt_year_column'])
require_columns(tdf,needed,'IFLS4 BLT record')
if t.get('program_selector_column'):
    if not t.get('program_selector_codes'):raise ValueError('Verified BLT program selector codes are required')
    tdf=tdf.loc[normalized(tdf[t['program_selector_column']]).isin([str(v) for v in t['program_selector_codes']])].copy()
if tdf.empty:raise ValueError('No BLT program records matched: check IFLS4 KSR file and codes')
tdf['hhid_ifls4']=normalized(tdf[t['household']]);tdf=tdf.loc[tdf['hhid_ifls4'].notna()].copy()
if tdf['hhid_ifls4'].duplicated().any():
    raise ValueError('Repeated BLT rows per IFLS4 household. Audit records before assigning treatment; no arbitrary deduplication.')
treated=set(map(str,t['treated_codes']));untreated=set(map(str,t['untreated_codes']))
if not treated or not untreated or treated&untreated:raise ValueError('Define disjoint explicit yes and no receipt codes from codebook.')
code=normalized(tdf[t['receipt_column']])
tdf['blt_2005']=pd.Series(pd.NA,index=tdf.index,dtype='Int64')
tdf.loc[code.isin(treated),'blt_2005']=1
tdf.loc[code.isin(untreated),'blt_2005']=0
if t.get('receipt_year_column'):
    y=normalized(tdf[t['receipt_year_column']]);allowed=set(map(str,t['receipt_year_codes']))
    uncertain=tdf['blt_2005'].eq(1).fillna(False) & (~y.isin(allowed))
    tdf.loc[uncertain,'blt_2005']=pd.NA
    print('Treatment yes with year outside allowed/missing:',int(uncertain.sum()))
master=master.merge(tdf[['hhid_ifls4','blt_2005']],on='hhid_ifls4',how='left',validate='many_to_one')

m=cfg['mediator']
mdf,_=stata(m['wave'],m['file'])
if m['wave']!='ifls4':raise ValueError('Mediator must precede 2014 welfare outcome')
if m.get('format')!='long':raise NotImplementedError('This build version supports long-form KP. Audit and reshape wide-form KP separately.')
require_columns(mdf,[m['pid'],m['item_column'],m['response_column']],'IFLS4 KP')
if len(m['item_code_map'])!=10 or any(v is None for v in m['item_code_map'].values()):
    raise ValueError('Verify all ten distinct CES-D item-type codes in config')
rev={str(v):name for name,v in m['item_code_map'].items()}
if len(rev)!=10:raise ValueError('CES-D item codes must be unique')
mdf['pidlink']=normalized(mdf[m['pid']]);mdf['item']=normalized(mdf[m['item_column']]).map(rev)
mdf=mdf.loc[mdf['pidlink'].notna() & mdf['item'].notna()].copy()
if mdf.duplicated(['pidlink','item']).any():raise ValueError('Repeated person-item observations in KP. Investigate source, not drop duplicates.')
valid=set(map(str,m['valid_response_codes']))
if not valid:raise ValueError('CES-D valid response codes not configured')
resp=normalized(mdf[m['response_column']]);mdf['response']=resp.where(resp.isin(valid))
wide=mdf.pivot(index='pidlink',columns='item',values='response').reset_index()
wide=wide.rename(columns={c:'cesd_'+c for c in m['item_code_map']})
items=['cesd_'+c for c in m['item_code_map']]
for x in items:
    if x not in wide.columns:wide[x]=pd.NA
wide['cesd_observed_items']=wide[items].notna().sum(axis=1)
master=master.merge(wide[['pidlink']+items+['cesd_observed_items']],on='pidlink',how='left',validate='one_to_one')

w=cfg['welfare'];wdf=read_local_csv(w['file'])
require_columns(wdf,[w['wave_column'],w['household_column'],w['pce_column'],w['poverty_line_column']],'harmonized welfare')
wdf=wdf.rename(columns={w['wave_column']:'wave',w['household_column']:'hhid',w['pce_column']:'monthly_pce',w['poverty_line_column']:'poverty_line'})
wdf['hhid']=normalized(wdf['hhid']);wdf['monthly_pce']=pd.to_numeric(wdf['monthly_pce'],errors='coerce')
wdf['poverty_line']=pd.to_numeric(wdf['poverty_line'],errors='coerce')
if wdf[['monthly_pce','poverty_line']].dropna().lt(0).any().any() or (wdf['poverty_line'].dropna()==0).any():
    raise ValueError('Invalid negative PCE / nonpositive poverty line')
wdf['log_pce_pl']=np.log(wdf['monthly_pce']/wdf['poverty_line'])
wdf.loc[wdf['monthly_pce'].le(0),'log_pce_pl']=np.nan
wdf['poor']=pd.Series(pd.NA,index=wdf.index,dtype='Int64')
wdf.loc[wdf['log_pce_pl'].notna(),'poor']=(wdf.loc[wdf['log_pce_pl'].notna(),'log_pce_pl']<0).astype(int)
for wave in ('ifls3','ifls5'):
    subset=wdf.loc[wdf['wave'].eq(wave),['hhid','monthly_pce','poverty_line','log_pce_pl','poor']].copy()
    if subset.empty:raise ValueError(f'Harmonized welfare has no rows for {wave}')
    assert_unique(subset,'hhid',f'{wave} welfare')
    rename={'hhid':f'hhid_{wave}', 'monthly_pce':f'pce_{wave}', 'poverty_line':f'pl_{wave}', 'log_pce_pl':f'log_welfare_{wave}', 'poor':f'poor_{wave}'}
    master=master.merge(subset.rename(columns=rename),on=f'hhid_{wave}',how='left',validate='many_to_one')
master['poverty_exit_2014']=pd.Series(pd.NA,index=master.index,dtype='Int64')
ok=master['poor_ifls3'].eq(1).fillna(False)&master['poor_ifls5'].notna()
master.loc[ok,'poverty_exit_2014']=(1-master.loc[ok,'poor_ifls5'].astype(int)).astype('Int64')
master['baseline_poor']=master['poor_ifls3'].eq(1).fillna(False)
master['observed_cesd']=master['cesd_observed_items'].fillna(0).gt(0)
master['eligible_all_core']=master['baseline_poor']&master['blt_2005'].notna()&master['observed_cesd']&master['log_welfare_ifls5'].notna()

checks=[('2000 baseline adults',len(master)),('baseline poor',int(master['baseline_poor'].sum())),
 ('linked current member in 2007',int(master['observed_ifls4'].sum())),
 ('linked current member in 2014',int(master['observed_ifls5'].sum())),
 ('verified BLT recorded',int(master['blt_2005'].notna().sum())),
 ('at least one CES-D item',int(master['observed_cesd'].sum())),
 ('2014 valid continuous welfare',int(master['log_welfare_ifls5'].notna().sum())),
 ('baseline poor + BLT known + CES-D + 2014 welfare',int(master['eligible_all_core'].sum()))]
save_report(pd.DataFrame(checks,columns=['check','n']),'04_panel_sample_flow.csv')
parts={
    'baseline_person_2000.csv':base,
    'blt2005_household_ifls4.csv':tdf[['hhid_ifls4','blt_2005']],
    'cesd_items_2007.csv':wide[['pidlink']+items+['cesd_observed_items']],
    'person_panel_full.csv':master
}
analysis=master.loc[master['baseline_poor']].copy() if cfg['analysis'].get('baseline_poor_only',True) else master.copy()
path=analysis_dir()/'baseline_poor_analysis_panel.csv'
existing=[str(intermediate_dir()/name) for name in parts if (intermediate_dir()/name).exists()]
if path.exists():existing.append(str(path))
if existing:
    raise FileExistsError('Previous analysis outputs exist. Back up/remove them before rebuilding: '+str(existing))
for name,frame in parts.items():save_private(frame,name)
analysis.to_csv(path,index=False)
print('CREATED private analysis panel:',path)
print('Next: check sample flow, BLT classification, CES-D item distributions and repeated household treatment exposure.')
print('STOP: these files are not causal-estimation ready until all design/identification diagnostics pass.')
