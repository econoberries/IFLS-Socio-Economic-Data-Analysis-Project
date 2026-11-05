"""Metadata-only audit of all .dta sources and all variables; no records exported."""
import re
import pandas as pd
from common import REQUIRED,STEMS,source_root,find_dta,save_report

rows=[];cols=[];suggest=[]
pattern=re.compile(r'cash|transfer|blt|benefit|poverty|poor|food|consum|expend|salary|wage|income|asset|health|depress|stress|educat|school|work|labor|employment|household|interview|member|province|urban|rural|year',re.I)
for wave in REQUIRED:
    folder=source_root()/wave
    files=sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower()=='.dta') if folder.exists() else []
    print(wave,':',len(files),'Stata files')
    for p in files:
        import pyreadstat
        try:
            _,meta=pyreadstat.read_dta(str(p),metadataonly=True,apply_value_formats=False)
            rows.append(dict(wave=wave,relative_path=str(p.relative_to(source_root())),stem=p.stem,rows=meta.number_rows,columns=len(meta.column_names),status='OK'))
            for v in meta.column_names:
                label=(meta.column_names_to_labels or {}).get(v) or ''
                item=dict(wave=wave,stem=p.stem,variable=v,label=label)
                cols.append(item)
                if pattern.search(v+' '+label):suggest.append(item)
        except Exception as err:
            rows.append(dict(wave=wave,relative_path=str(p.relative_to(source_root())),stem=p.stem,rows=None,columns=None,status=f'ERROR {type(err).__name__}: {str(err)[:150]}'))
    for stem in STEMS[wave]:
        if find_dta(wave,stem,required=False) is None:
            print('  Candidate missing:',wave,stem)
save_report(pd.DataFrame(rows),'01_file_inventory.csv')
save_report(pd.DataFrame(cols),'01_all_variable_dictionary.csv')
save_report(pd.DataFrame(suggest),'01_research_variable_candidates.csv')
summary=[]
for wave in REQUIRED:
    for stem in STEMS[wave]:
        summary.append(dict(wave=wave,stem=stem,available=find_dta(wave,stem,required=False) is not None))
save_report(pd.DataFrame(summary),'01_study_module_checklist.csv')
print('Check 01_study_module_checklist.csv. Missing modules may be absent, differently named, or not required by your final model.')
