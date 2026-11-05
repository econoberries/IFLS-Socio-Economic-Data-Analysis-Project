"""Audit critical modules/response codes and unfiltered panel ID overlap."""
import pandas as pd
from common import normalized,stata,find_dta,save_report,txt

inspect={
 'ifls3':['bk_ar1','b1_ks0','b1_ks1','b1_ks2','b1_ks3','b2_kr','b3a_tk'],
 'ifls4':['bk_ar1','b1_ksr1','b1_ksr3','b1_ksr4','b3b_kp'],
 'ifls5':['bk_ar1','b1_ks0','b1_ks1','b1_ks2','b1_ks3','b3b_kp']}
selected=['ar01a','kptype','kp02','ksr3type','ksr1type','ksr2type','ksr17','ksr18y','ksr18m','ksr22y','ksr22m']
code_rows=[];card=[];rosters={}
for wave,stems in inspect.items():
    for stem in stems:
        if find_dta(wave,stem,required=False) is None:continue
        df,meta=stata(wave,stem)
        card.append(dict(wave=wave,file=stem,rows=len(df),columns=df.shape[1]))
        labels=meta.variable_value_labels or {}
        columns=[v for v in df if v.lower() in selected or v.lower().startswith(('ksr','kp'))]
        for v in columns:
            freq=normalized(df[v]).fillna('<MISSING>').value_counts(dropna=False).head(50)
            mapping={txt(k):str(lab) for k,lab in labels.get(v,{}).items()}
            for code,n in freq.items():
                code_rows.append(dict(wave=wave,file=stem,variable=v,code=code,label=mapping.get(str(code),''),n=int(n)))
        if stem=='bk_ar1' and 'pidlink' in df.columns:
            ids=normalized(df['pidlink']).dropna()
            rosters[wave]=set(ids.tolist())
            card += [dict(wave=wave,file=stem,rows=int(ids.duplicated().sum()),columns=None,note='duplicate unfiltered pidlink rows'),
                     dict(wave=wave,file=stem,rows=int(ids.nunique()),columns=None,note='unique pidlinks unfiltered')]
save_report(pd.DataFrame(card),'02_critical_file_counts.csv')
save_report(pd.DataFrame(code_rows),'02_response_code_frequencies.csv')
link=[]
for a,b in [('ifls3','ifls4'),('ifls4','ifls5'),('ifls3','ifls5')]:
    if a in rosters and b in rosters:
        link.append(dict(waves=a+'-'+b,overlap_unfiltered=len(rosters[a]&rosters[b])))
save_report(pd.DataFrame(link),'02_unfiltered_pidlink_overlap.csv')
print('IMPORTANT: raw PIDLINK overlap is not the final linked sample. Filter current membership before merges.')
print('Review IFLS4 KSR files to determine BLT 2005 receipt codes and population at risk; no codes are assumed.')
print('Review KP item codes and missing categories; do not sum unverified CES-D responses.')
