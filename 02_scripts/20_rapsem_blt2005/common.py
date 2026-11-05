"""Shared read-only source access. All raw IFLS microdata stays local."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

STUDY = 'rapsem_blt2005'
REQUIRED = ('ifls3','ifls4','ifls5')
STEMS = {
    'ifls3': ['bk_ar1','bk_ar0','bk_krk','b1_ks0','b1_ks1','b1_ks2','b1_ks3','b2_kr','b2_hr','b2_ut','b2_nt','b3a_dl','b3a_tk','b3b_kk','b3b_ma'],
    'ifls4': ['bk_ar1','bk_ar0','bk_krk','b1_ks0','b1_ks1','b1_ks2','b1_ks3','b1_ksr1','b1_ksr3','b1_ksr4','b2_kr','b2_hr','b3a_dl','b3a_tk','b3b_kp','ptrack'],
    'ifls5': ['bk_ar1','bk_ar0','bk_krk','b1_ks0','b1_ks1','b1_ks2','b1_ks3','b1_ksr1','b2_kr','b2_hr','b3a_dl','b3a_tk','b3b_kp','ptrack'],
}

def project_root() -> Path:
    here = Path.cwd().resolve()
    for candidate in (here,*here.parents):
        if (candidate/'IFLS_Project.Rproj').is_file() and (candidate/'01_data').is_dir():
            return candidate
    raise SystemExit('Run from inside the existing IFLS project (folder containing IFLS_Project.Rproj).')

def source_root() -> Path:
    return project_root()/'01_data'/'01_raw_dta'

def output_dir() -> Path:
    p = project_root()/'05_outputs'/'tables'/STUDY
    p.mkdir(parents=True,exist_ok=True)
    return p

def intermediate_dir() -> Path:
    p = project_root()/'01_data'/'04_intermediate'/STUDY
    p.mkdir(parents=True,exist_ok=True)
    return p

def analysis_dir() -> Path:
    p = project_root()/'01_data'/'05_analysis'/STUDY
    p.mkdir(parents=True,exist_ok=True)
    return p

def script_dir() -> Path:
    return Path(__file__).resolve().parent

def find_dta(wave:str, stem:str, required:bool=True) -> Path|None:
    folder=source_root()/wave
    matches=sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower()=='.dta' and p.stem.casefold()==stem.casefold()) if folder.exists() else []
    if len(matches)>1:
        raise ValueError(f'Ambiguous {wave}/{stem}: {matches}. Remove duplicate extractions before continuing.')
    if not matches:
        if required: raise FileNotFoundError(f'No {stem}.dta found recursively under {folder}')
        return None
    return matches[0]

def stata(wave,stem,metadataonly=False,usecols=None):
    import pyreadstat
    fn=find_dta(wave,stem)
    kwargs=dict(apply_value_formats=False,user_missing=True,metadataonly=metadataonly)
    if usecols is not None and not metadataonly:
        kwargs['usecols']=list(usecols)
    return pyreadstat.read_dta(str(fn),**kwargs)

def txt(val):
    if pd.isna(val):return None
    if isinstance(val,str):
        val=val.strip()
        return val or None
    if isinstance(val,(int,float)) and float(val).is_integer():return str(int(val))
    return str(val).strip() or None

def normalized(series):
    return series.map(txt).astype('string')

def require_columns(df, names, context):
    missing=[x for x in names if not x or x not in df.columns]
    if missing: raise ValueError(f'{context}: missing/unconfigured column(s) {missing}. Review audit CSV and codebooks.')

def assert_unique(df,col,context):
    if df[col].isna().any() or df[col].duplicated().any():
        raise ValueError(f'{context}: {col} must be nonmissing and unique. Check current-member codes/duplicate source records.')

def save_private(df,filename):
    p=intermediate_dir()/filename
    if p.exists():raise FileExistsError(f'{p} exists. Do not overwrite unreviewed analysis data; rename/back up it first.')
    df.to_csv(p,index=False)
    print('CREATED private file:',p)
    return p

def save_report(df,filename):
    p=output_dir()/filename
    df.to_csv(p,index=False)
    print('Audit report:',p)
    return p

def read_config():
    p=script_dir()/'study_config.json'
    if not p.exists():raise FileNotFoundError('Copy study_config.example.json to study_config.json and complete verified mappings.')
    return json.loads(p.read_text(encoding='utf-8'))

def approved(section):
    if not section.get('approved',False):
        raise ValueError('A required configuration section is not approved. Check its variables and codes against codebook first.')

def read_local_csv(path):
    p=project_root()/path
    if not p.is_file():raise FileNotFoundError(p)
    return pd.read_csv(p,dtype='string')
